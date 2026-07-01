import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from SRACore.util.const import AppDataDir


# Runtime coordination files are the small cross-process contract between
# SRA.exe, SRAFrontend.Server, and the Python/CLI task runner.
#
# The UI process and server process are not guaranteed to own the task process:
# a task can be started from SRA.exe, from WebUI, or directly from the CLI.  A
# process-local singleton would therefore only describe one launcher, not the
# real task state.  These files live in AppData so every entry point can observe
# the same state without keeping another always-on broker process.
#
# File roles:
# - sra-session.json: last known active task session and heartbeat.
# - stop.request: cooperative stop signal written by WebUI/SRA.exe and polled by
#   the task runner.
# - task.lock: best-effort single-task guard across launchers.
RuntimeDir = AppDataDir / "runtime"
SessionFile = RuntimeDir / "sra-session.json"
StopRequestFile = RuntimeDir / "stop.request"
LockFile = RuntimeDir / "task.lock"


def _atomic_write(path: Path, text: str) -> None:
    """Replace a runtime file atomically so observers never read half JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)


def _is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_session() -> dict[str, Any] | None:
    try:
        if not SessionFile.exists():
            return None
        data = json.loads(SessionFile.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None


def is_session_active(max_age_seconds: float = 10.0) -> bool:
    """Return whether the session still represents a live task process.

    The heartbeat window intentionally stays short.  It lets SRA.exe/WebUI show
    a stale/exited state quickly after a crash while still tolerating normal task
    loop delays.
    """
    session = read_session()
    if not session:
        return False
    if session.get("state") not in ("running", "stopping"):
        return False
    try:
        last_heartbeat = float(session.get("lastHeartbeatUnix", 0))
        pid = int(session.get("pid", 0))
    except (TypeError, ValueError):
        return False
    return time.time() - last_heartbeat <= max_age_seconds and _is_process_alive(pid)


class RuntimeSession:
    """Owns one cooperative task session written by the Python task runner."""

    def __init__(self, owner: str, mode: str, config_names: list[str] | None = None, task_name: str | None = None):
        self.session_id = uuid.uuid4().hex
        self.owner = owner
        self.mode = mode
        self.config_names = config_names or []
        self.task_name = task_name
        self.started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        self.started_at_unix = time.time()
        self.state = "running"
        self._lock_acquired = False

    def start(self) -> bool:
        """Acquire the cross-launcher lock and publish the first heartbeat."""
        RuntimeDir.mkdir(parents=True, exist_ok=True)
        if not self._acquire_lock():
            return False
        self._write()
        try:
            StopRequestFile.unlink(missing_ok=True)
        except Exception:
            pass
        return True

    def heartbeat(self) -> None:
        self._write()

    def mark_stopping(self) -> None:
        # Keep the session visible as "stopping" until the task loop unwinds.
        self.state = "stopping"
        self._write()

    def finish(self, state: str = "completed") -> None:
        # A terminal state is written before releasing the lock so late readers
        # can distinguish a clean finish from an unexpected process exit.
        self.state = state
        self._write()
        try:
            StopRequestFile.unlink(missing_ok=True)
        except Exception:
            pass
        self._release_lock()

    def stop_requested(self) -> bool:
        return StopRequestFile.exists()

    def _write(self) -> None:
        now = time.time()
        # schemaVersion is deliberately present from the first revision so the
        # C# reader can evolve this file format without guessing field meaning.
        payload = {
            "schemaVersion": 1,
            "sessionId": self.session_id,
            "pid": os.getpid(),
            "owner": self.owner,
            "mode": self.mode,
            "configNames": self.config_names,
            "taskName": self.task_name,
            "state": self.state,
            "startedAt": self.started_at,
            "startedAtUnix": self.started_at_unix,
            "lastHeartbeat": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "lastHeartbeatUnix": now,
        }
        _atomic_write(SessionFile, json.dumps(payload, ensure_ascii=False, indent=2))

    def _acquire_lock(self) -> bool:
        if is_session_active():
            return False
        try:
            LockFile.unlink(missing_ok=True)
        except Exception:
            pass

        payload = json.dumps(
            {"sessionId": self.session_id, "pid": os.getpid(), "createdAtUnix": time.time()},
            ensure_ascii=False,
        )
        try:
            # O_EXCL makes the first writer win even if SRA.exe and WebUI start a
            # task at nearly the same time.
            fd = os.open(str(LockFile), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                file.write(payload)
            self._lock_acquired = True
            return True
        except FileExistsError:
            return not is_session_active() and self._replace_stale_lock(payload)
        except Exception:
            return False

    def _replace_stale_lock(self, payload: str) -> bool:
        try:
            LockFile.unlink(missing_ok=True)
            fd = os.open(str(LockFile), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                file.write(payload)
            self._lock_acquired = True
            return True
        except Exception:
            return False

    def _release_lock(self) -> None:
        if not self._lock_acquired:
            return
        try:
            LockFile.unlink(missing_ok=True)
        except Exception:
            pass
        self._lock_acquired = False


def request_stop(source: str = "unknown") -> None:
    """Ask the active task runner to stop without killing its process.

    This is used for bidirectional control: WebUI can stop a task started from
    SRA.exe, and SRA.exe can stop a task started from WebUI, because both write
    the same cooperative stop request file.
    """
    payload = {
        "source": source,
        "requestedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "requestedAtUnix": time.time(),
    }
    _atomic_write(StopRequestFile, json.dumps(payload, ensure_ascii=False, indent=2))

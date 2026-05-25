import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
from types import SimpleNamespace

import pytest

import main
from SRACore.util.const import VERSION


def test_main_version_option_exits_cleanly(monkeypatch, capsys):
    """main.py should print the version and exit when --version is used."""

    monkeypatch.setattr(main, "load_app_settings", lambda: SimpleNamespace(Display=SimpleNamespace(language=0)))
    monkeypatch.setattr(main.Resource, "set_language", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main.sys, "argv", ["main.py", "--version"])

    with pytest.raises(SystemExit) as exc_info:
        main.main()

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert captured.out.strip() == VERSION


def test_main_version_option_works_in_real_process():
    """main.py should also exit cleanly when launched as a real subprocess."""

    repo_root = Path(__file__).resolve().parents[1]
    temp_root = repo_root / ".pytest_runtime" / f"version_{uuid4().hex}"
    if sys.platform == "win32":
        app_root = temp_root / "SRA"
    else:
        app_root = temp_root / ".config" / "SRA"

    try:
        app_root.mkdir(parents=True, exist_ok=True)
        (app_root / "settings.json").write_text(json.dumps({}), encoding="utf-8")

        env = os.environ.copy()
        env["APPDATA"] = str(temp_root)
        env["HOME"] = str(temp_root)

        result = subprocess.run(
            [sys.executable, "main.py", "--version"],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        assert result.returncode == 0
        assert result.stdout.strip() == VERSION
    finally:
        shutil.rmtree(temp_root.parent, ignore_errors=True)



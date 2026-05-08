from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from SRACore.util.const import AppDataDir
from SRACore.util.logger import logger

_STATE_PATH: Path = AppDataDir / "cosmic_strife_policy_state.json"

# 与多数日常任务重置时间一致：本地时间未到当日 04:00 仍算「昨日」账本
_GAME_DAY_BOUNDARY = time(4, 0)


def game_calendar_date_local() -> date:
    """本地时间下以凌晨 4 点为界的「任务日」日期。"""
    now = datetime.now()
    boundary = datetime.combine(now.date(), _GAME_DAY_BOUNDARY)
    if now < boundary:
        return now.date() - timedelta(days=1)
    return now.date()


@dataclass
class ModuleRunCounters:
    daily_date: str = ""  # YYYY-MM-DD
    daily_runs: int = 0
    week_key: str = ""  # e.g. 2026-W19
    weekly_runs: int = 0


@dataclass
class CosmicStrifePolicyState:
    du: ModuleRunCounters = field(default_factory=ModuleRunCounters)
    cw: ModuleRunCounters = field(default_factory=ModuleRunCounters)


def _week_key_today() -> str:
    y, w, _ = date.today().isocalendar()
    return f"{y}-W{w:02d}"


def _roll_counters(c: ModuleRunCounters) -> None:
    today = game_calendar_date_local().isoformat()
    if c.daily_date != today:
        c.daily_date = today
        c.daily_runs = 0
    wk = _week_key_today()
    if c.week_key != wk:
        c.week_key = wk
        c.weekly_runs = 0


def load_policy_state() -> CosmicStrifePolicyState:
    try:
        if not _STATE_PATH.is_file():
            return CosmicStrifePolicyState()
        raw = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
        du = _parse_module(raw.get("du", {}))
        cw = _parse_module(raw.get("cw", {}))
        return CosmicStrifePolicyState(du=du, cw=cw)
    except Exception as e:
        logger.warning(f"读取旷宇纷争策略状态失败，将使用空状态: {e}")
        return CosmicStrifePolicyState()


def _parse_module(d: dict[str, Any]) -> ModuleRunCounters:
    return ModuleRunCounters(
        daily_date=str(d.get("daily_date", "")),
        daily_runs=int(d.get("daily_runs", 0)),
        week_key=str(d.get("week_key", "")),
        weekly_runs=int(d.get("weekly_runs", 0)),
    )


def save_policy_state(state: CosmicStrifePolicyState) -> None:
    payload = {"du": asdict(state.du), "cw": asdict(state.cw)}
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(_STATE_PATH.parent), suffix=".tmp", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, _STATE_PATH)
    except Exception as e:
        logger.error(f"写入旷宇纷争策略状态失败: {e}")
        try:
            Path(tmp).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def register_completed_run(module: ModuleRunCounters) -> None:
    _roll_counters(module)
    module.daily_runs += 1
    module.weekly_runs += 1


def remaining_daily(cap: int, module: ModuleRunCounters) -> int:
    _roll_counters(module)
    if cap <= 0:
        return 0
    return max(0, cap - module.daily_runs)


def remaining_weekly(cap: int, module: ModuleRunCounters) -> int:
    _roll_counters(module)
    if cap <= 0:
        return 0
    return max(0, cap - module.weekly_runs)

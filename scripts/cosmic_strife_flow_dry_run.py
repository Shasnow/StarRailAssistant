#!/usr/bin/env python3
"""
旷宇纷争流程 dry-run：验证 CosmicStrifeTask + 周期 OCR 相关调度，不跑真实战斗。

用法（在项目根目录）:
  python scripts/cosmic_strife_flow_dry_run.py
  python scripts/cosmic_strife_flow_dry_run.py --deep
  python scripts/cosmic_strife_flow_dry_run.py --quick --fill-only

模式说明:
  --quick  将 DifferentialUniverse.run / CurrencyWars.run 整体替换为立即成功，
            仅考察 CosmicStrifeTask 外层（指南探测、次数解析、循环结构）。
  --deep   保留真实 run()，仅.patch:
            - 差分: _navigate_and_fight → True（跳过战斗/移动）
            - 货币战争: game_loop → 空（跳过局内）
            从而走过「进战斗前」与「结算/收尾」附近的调用链（依赖下方 DryRunOperator 对图像接口的快速返回）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# 项目根：…/StarRailAssistant-full
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loguru import logger


class DryRunOperator:
    """最小 Operator：图像等待一律快速成功，OCR 返回可解析的周期字符串。"""

    def __init__(self, cycle_text: str = "18000/18000"):
        self.settings = MagicMock()
        self.settings.General.hotkeyF4 = "f4"
        self.settings.Notification.onStart = []
        self.settings.Notification.onComplete = []
        self.settings.Notification.onFailure = []
        self.stop_event = None
        self.width = 1920
        self.height = 1080
        self._cycle_text = cycle_text
        self.calls: list[tuple[str, tuple, dict]] = []

    def _log(self, name: str, *args, **kwargs):
        self.calls.append((name, args, kwargs))

    def sleep(self, *a, **k):
        self._log("sleep", a, k)

    def press_key(self, *a, **k):
        self._log("press_key", a, k)

    def click_img(self, *a, **k):
        self._log("click_img", a, k)
        return True

    def click_box(self, *a, **k):
        self._log("click_box", a, k)
        return True

    def click_point(self, *a, **k):
        self._log("click_point", a, k)
        return True

    def wait_img(self, *a, **k):
        self._log("wait_img", a, k)
        return MagicMock()

    def do_while(self, *a, **k):
        self._log("do_while", a, k)

    def locate(self, *a, **k):
        self._log("locate", a, k)
        return None

    def wait_any_img(self, imgs, interval=0.5, **kwargs):
        self._log("wait_any_img", (imgs,), {"interval": interval, **kwargs})
        n = len(imgs) if imgs is not None else 0
        # periodic_progress.navigate：5 张图里 index 0 为大地图 ENTER，需先回到地图再 F4
        if n >= 5:
            return 0, MagicMock()
        # DU.page_locate：2 张 → index 1 表示已在差分入口界面
        if n == 2:
            return 1, MagicMock()
        # CW.page_locate：4 张 → index 1 为 START_CURRENCY_WARS
        if n == 4:
            return 1, MagicMock()
        # DU.select：约 9 张 → 返回退出项（终端），尽快结束祝福链
        if n >= 9:
            return (8, MagicMock())
        return 1, MagicMock()

    def ocr(self, *a, **k):
        self._log("ocr", a, k)
        # 单行即可被 parse_cycle_progress_from_texts 解析
        return [[None, self._cycle_text]]


def _base_config() -> dict:
    return {
        "DUEnable": True,
        "DUPolicy": 2,
        "DURunTimes": 2,
        "DUWeeklyTotalCap": 20,
        "DUUseTechnique": False,
        "CurrencyWarsEnable": True,
        "CurrencyWarsPolicy": 2,
        "CurrencyWarsRunTimes": 2,
        "CurrencyWarsWeeklyTotalCap": 3,
        "CurrencyWarsObjective": 0,
        "CurrencyWarsRuleset": 0,
        "CurrencyWarsMode": 0,
        "CurrencyWarsUsername": "DryRun",
        "CurrencyWarsStrategy": "template",
        "CurrencyWarsDifficulty": 0,
    }


def run_quick(cfg: dict, *, cycle_text: str):
    """外层调度 + 指南探测逻辑；DU/CW.run 整条替换。"""
    from tasks.CosmicStrifeTask import CosmicStrifeTask

    op = DryRunOperator(cycle_text=cycle_text)

    def fake_du_run(self):
        logger.info("[dry-run][DU] DifferentialUniverse.run → 跳过（不进入战斗流水线）")
        return True

    def fake_cw_run(self):
        logger.info("[dry-run][CW] CurrencyWars.run → 跳过（不进入对局流水线）")
        return True

    with patch(
        "tasks.differential_universe.DifferentialUniverse.DifferentialUniverse.run",
        fake_du_run,
    ):
        with patch("tasks.currency_wars.CurrencyWars.CurrencyWars.run", fake_cw_run):
            t = CosmicStrifeTask(op, cfg)
            ok = t.run()
    logger.info(f"[dry-run] CosmicStrifeTask.run 结束，结果: {ok}")
    logger.info(f"[dry-run] operator 调用次数: {len(op.calls)}（见 op.calls）")


def run_deep(cfg: dict, *, cycle_text: str):
    """保留 DU/CW.run 外壳与 page_locate；跳过战斗、结算细节、局内博弈。
    另跳过「进入关卡」与祝福选择链（图像依赖多），避免 dry-run 在无真实客户端时卡死。"""
    from tasks.CosmicStrifeTask import CosmicStrifeTask
    from tasks.differential_universe.DifferentialUniverse import DifferentialUniverse
    from tasks.currency_wars.CurrencyWars import CurrencyWars

    op = DryRunOperator(cycle_text=cycle_text)

    def skip_fight(self):
        logger.info("[dry-run][DU] _navigate_and_fight → True（跳过战斗/移动）")
        return True

    def skip_complete(self):
        logger.info("[dry-run][DU] _complete_mission → True（跳过结算界面等待）")
        return True

    def skip_start_du(_self, _exe_time):
        logger.info("[dry-run][DU] _start_differential_universe → True（跳过进入副本按钮链）")
        return True

    def skip_select(_self):
        logger.info("[dry-run][DU] select → True（跳过祝福/面具选择链）")
        return True

    def skip_game_loop(self):
        logger.info("[dry-run][CW] game_loop → 跳过（跳过局内博弈）")

    def skip_start_game(_self):
        logger.info("[dry-run][CW] start_game → True（跳过从大厅点「开始」进入对局）")
        return True

    def skip_handle_ending(_self):
        logger.info("[dry-run][CW] handle_ending → 跳过等待 START/ESC（dry-run）")

    with patch.object(DifferentialUniverse, "_navigate_and_fight", skip_fight):
        with patch.object(DifferentialUniverse, "_complete_mission", skip_complete):
            with patch.object(DifferentialUniverse, "_start_differential_universe", skip_start_du):
                with patch.object(DifferentialUniverse, "select", skip_select):
                    with patch.object(CurrencyWars, "game_loop", skip_game_loop):
                        with patch.object(CurrencyWars, "start_game", skip_start_game):
                            with patch.object(CurrencyWars, "handle_ending", skip_handle_ending):
                                t = CosmicStrifeTask(op, cfg)
                                ok = t.run()
    logger.info(f"[dry-run][deep] CosmicStrifeTask.run 结束，结果: {ok}")


def main():
    parser = argparse.ArgumentParser(description="旷宇纷争流程 dry-run")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="仅跳过战斗.game_loop / _navigate_and_fight，保留 run() 前后逻辑",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="整条 DU.run/CW.run 替换为空成功（最快）",
    )
    parser.add_argument(
        "--full-cycle",
        action="store_true",
        help="Mock OCR 使用 18000/18000（模拟已满）",
    )
    parser.add_argument(
        "--quiet-log",
        action="store_true",
        help="仅输出 WARNING 及以上",
    )
    args = parser.parse_args()

    cfg = _base_config()
    cycle_text = "18000/18000" if args.full_cycle else "9000/18000"

    logger.remove()
    logger.add(sys.stderr, level="WARNING" if args.quiet_log else "INFO")

    if args.deep and args.quick:
        logger.error("请只选 --quick 或 --deep 之一")
        sys.exit(2)

    if args.deep:
        run_deep(cfg, cycle_text=cycle_text)
    elif args.quick:
        run_quick(cfg, cycle_text=cycle_text)
    else:
        run_quick(cfg, cycle_text=cycle_text)


if __name__ == "__main__":
    main()

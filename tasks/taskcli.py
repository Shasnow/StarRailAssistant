import argparse
import json
import tomllib

import cmd2

from SRACore.cli2 import SRACli
from SRACore.util.const import AppRootDir


class TrailblazePowerCommands(cmd2.CommandSet[SRACli]):
    DEFAULT_CATEGORY = 'Trailblaze Power'

    @staticmethod
    def _build_tpconfig_parser() -> cmd2.Cmd2ArgumentParser:
        parser = cmd2.Cmd2ArgumentParser(description='查看开拓力副本配置')
        parser.add_argument('--json', action='store_true', help='以JSON格式输出')
        parser.add_argument('subtask', nargs='?', help='指定子任务名称（如 calyx_golden）')
        return parser

    @cmd2.with_argparser(_build_tpconfig_parser)
    def do_tpconfig(self, args: argparse.Namespace) -> None:
        config_path = AppRootDir / "tasks" / "config" / "trailblaze_power.toml"
        if not config_path.exists():
            self._cmd.err(f"配置文件不存在: {config_path}")
            return

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        subtasks: dict = config.get("subtasks", {})

        if args.subtask:
            if args.subtask not in subtasks:
                self._cmd.err(f"未找到子任务: {args.subtask}")
                return
            subtasks = {args.subtask: subtasks[args.subtask]}

        def format_subtasks(data: dict) -> str:
            lines = []
            for key, st in data.items():
                lines.append(f"[{key}] {st['name']}")
                lines.append(f"  函数: {st['func']}  体力消耗: {st['cost']}  最大次数: {st['max_count']}")
                lines.append(f"  关卡:")
                for lv in st.get("levels", []):
                    lines.append(f"    {lv['id']:>2}. {lv['name']} → {lv['result']}")
                lines.append("")
            return "\n".join(lines)

        self._cmd.ok("开拓力副本配置", subtasks, formatter=format_subtasks)


class CurrencyWarsCommands(cmd2.CommandSet[SRACli]):
    DEFAULT_CATEGORY = 'Currency Wars'

    @staticmethod
    def _build_strategy_parser() -> cmd2.Cmd2ArgumentParser:
        strategy_description = '管理货币战争攻略'
        strategy_parser = cmd2.Cmd2ArgumentParser(description=strategy_description)
        strategy_parser.add_subparsers(metavar="SUBCOMMAND", help="子命令", required=True)
        return strategy_parser

    @cmd2.with_argparser(_build_strategy_parser)
    def do_strategy(self, args: argparse.Namespace) -> None:
        args.cmd2_subcommand_func(args)

    @staticmethod
    def _build_strategy_list_parser() -> cmd2.Cmd2ArgumentParser:
        parser = cmd2.Cmd2ArgumentParser(description='列出所有攻略')
        parser.add_argument('--json', action='store_true', help='以JSON格式输出')
        return parser

    @cmd2.as_subcommand_to("strategy", "list", _build_strategy_list_parser(), help='列出所有攻略')
    def _strategy_list(self, _: argparse.Namespace) -> None:
        strategies_dir = AppRootDir / "tasks" / "currency_wars" / "strategies"
        if not strategies_dir.exists():
            self._cmd.err(f"攻略目录不存在: {strategies_dir}")
            return

        strategies = []
        for file in sorted(strategies_dir.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                data["file"] = file.stem
                strategies.append(data)
            except (json.JSONDecodeError, OSError) as e:
                self._cmd.err(f"加载 {file.name} 失败: {e}")

        if not strategies:
            self._cmd.ok("未找到任何攻略")
            return

        def format_strategies(items: list[dict]) -> str:
            lines = []
            for i, s in enumerate(items):
                on_field = ", ".join(f"{k}(★{v})" for k, v in s["on_field"].items())
                off_field = ", ".join(f"{k}(★{v})" for k, v in s["off_field"].items())
                lines.append(f"[{i + 1}] {s['title']}")
                lines.append(f"  文件: {s['file']}  作者: {s['author']}  最低金币: {s['min_coins']}  最低等级: {s['min_level']}")
                lines.append(f"  前台: {on_field}")
                lines.append(f"  后台: {off_field}")
                lines.append(f"  描述: {s['description'][:20]}...")
                lines.append("")
            return "\n".join(lines)

        self._cmd.ok(f"已找到 {len(strategies)} 个攻略", strategies, formatter=format_strategies)



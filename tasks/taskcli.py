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
            if args.json:
                self._cmd.poutput("{}")
            else:
                self._cmd.perror(f"配置文件不存在: {config_path}")
            return

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        subtasks: dict = config.get("subtasks", {})

        if args.subtask:
            if args.subtask not in subtasks:
                if args.json:
                    self._cmd.poutput("{}")
                else:
                    self._cmd.perror(f"未找到子任务: {args.subtask}")
                return
            subtasks = {args.subtask: subtasks[args.subtask]}

        if args.json:
            self._cmd.poutput(json.dumps(subtasks))
            return

        for key, st in subtasks.items():
            self._cmd.poutput(f"[{key}] {st['name']}")
            self._cmd.poutput(f"    函数: {st['func']}  体力消耗: {st['cost']}  最大次数: {st['max_count']}")
            self._cmd.poutput(f"    关卡:")
            for lv in st.get("levels", []):
                self._cmd.poutput(f"      {lv['id']:>2}. {lv['name']} → {lv['result']}")
            self._cmd.poutput("")


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
    def _strategy_list(self, args: argparse.Namespace) -> None:
        from pathlib import Path
        strategies_dir = AppRootDir / "tasks" / "currency_wars" / "strategies"
        if not strategies_dir.exists():
            if args.json:
                self._cmd.poutput("[]")
            else:
                self._cmd.perror(f"攻略目录不存在: {strategies_dir}")
            return

        strategies = []
        for file in sorted(strategies_dir.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                data["file"] = file.stem
                strategies.append(data)
            except (json.JSONDecodeError, OSError) as e:
                self._cmd.perror(f"加载 {file.name} 失败: {e}")

        if args.json:
            self._cmd.poutput(json.dumps(strategies))
            return

        if not strategies:
            self._cmd.poutput("未找到任何攻略")
            return

        for i, s in enumerate(strategies):
            on_field = ", ".join(f"{k}(★{v})" for k, v in s["on_field"].items())
            off_field = ", ".join(f"{k}(★{v})" for k, v in s["off_field"].items())
            self._cmd.poutput(f"[{i + 1}] {s['title']}")
            self._cmd.poutput(f"    文件: {s['file']}  作者: {s['author']}  最低金币: {s['min_coins']}  最低等级: {s['min_level']}")
            self._cmd.poutput(f"    前台: {on_field}")
            self._cmd.poutput(f"    后台: {off_field}")
            if s["description"]:
                desc = s["description"][:20] + ("..." if len(s["description"]) > 20 else "")
                self._cmd.poutput(f"    {desc}")
            self._cmd.poutput("")



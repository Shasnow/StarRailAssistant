import argparse
import json
import sys
from collections.abc import Callable
from typing import Any

import cmd2
from rich.text import Text

from SRACore.localization import Resources
from SRACore.services.app_context import AppContext
from SRACore.util import reload_package
from SRACore.util.const import VERSION, CORE, SettingsJson


class SRACli(cmd2.Cmd):
    DEFAULT_CATEGORY = Resources.cli_buildInCategory

    def __init__(self, context: AppContext):
        super().__init__(startup_script=".srarc",
                         auto_load_commands=True)
        self.intro = Resources.cli_intro(VERSION, CORE)
        self.prompt = 'sra> '
        self.default_error = Resources.cli_defaultError
        self.context = context
        self.settings = context.settings
        self._use_json: bool = False

        # 移除不需要的 settable 选项
        # for attr in ["debug", "timing", "quiet", "feedback_to_output",
        #               "max_completion_items", "allow_style", "always_show_hint",
        #               "scripts_add_to_history", "echo"]:
        #     self.remove_settable(attr)

        # 移除不需要的内置命令
        for cmd_name in ["run_pyscript"]:
            if hasattr(cmd2.Cmd, f"do_{cmd_name}"):
                delattr(cmd2.Cmd, f"do_{cmd_name}")

        # 任务/扩展编排与全局键盘监听由 AppContext 统一持有
        self.task_manager = context.task_manager
        self.extension_config_manager = context.extension_config_manager
        self.extension_runner = context.extension_runner

    def precmd(self, statement: cmd2.Statement | str) -> cmd2.Statement:
        """在执行命令前检查是否需要使用 JSON 输出"""
        self._use_json = '--json' in getattr(statement, 'raw', statement)
        return super().precmd(statement)

    # region 任务管理
    @staticmethod
    def _build_task_parser() -> cmd2.Cmd2ArgumentParser:
        task_description = Text.assemble(Resources.task_description)
        task_parser = cmd2.Cmd2ArgumentParser(description=task_description)
        task_parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return task_parser

    @cmd2.with_argparser(_build_task_parser, preserve_quotes=True)
    def do_task(self, args: argparse.Namespace) -> None:
        args.cmd2_subcommand_func(args)

    @staticmethod
    def _build_task_run_parser() -> cmd2.Cmd2ArgumentParser:
        task_run_parser = SRACli.cmd2argumentparser_factory(description=Text.assemble(Resources.run_description))
        task_run_parser.add_argument('config', nargs='*', help=Resources.run_configHelp)
        return task_run_parser

    @cmd2.as_subcommand_to("task", "run", _build_task_run_parser, help=Resources.run_description)
    def _task_run(self, args: argparse.Namespace) -> None:
        if self.context.is_busy():
            self.err(Resources.cli_task_taskAlreadyRunning)
            return
        self.context.run_configs(list(args.config))

    @staticmethod
    def _build_task_single_parser() -> cmd2.Cmd2ArgumentParser:
        task_single_parser = SRACli.cmd2argumentparser_factory(description=Text.assemble(Resources.single_description))
        task_single_parser.add_argument('task', help=Resources.single_taskHelp)
        task_single_parser.add_argument('--config', help=Resources.single_configHelp)
        return task_single_parser

    @cmd2.as_subcommand_to("task", "single", _build_task_single_parser, help=Resources.single_description)
    def _task_single(self, args: argparse.Namespace) -> None:
        if self.context.is_busy():
            self.err(Resources.cli_task_taskAlreadyRunning)
            return
        if self.context.run_single(args.task, args.config):
            self.ok(Resources.cli_run_started)

    @staticmethod
    def _build_task_stop_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description=Text.assemble(Resources.stop_description))

    @cmd2.as_subcommand_to("task", "stop", _build_task_stop_parser, help=Resources.stop_description)
    def _task_stop(self, _) -> None:
        # 任务与扩展共用全局工作线程，AppContext 会同时向两个 Runner 请求停止并等待结束
        self.context.stop_running_work()

    @staticmethod
    def _build_task_status_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description=Resources.cli_task_statusDescription)

    @cmd2.as_subcommand_to("task", "status", _build_task_status_parser, help=Resources.cli_task_statusDescription)
    def _task_status(self, _: argparse.Namespace) -> None:
        data = self.context.task_status()

        def format_info(info: dict[str, Any]) -> str:
            return (f"{Resources.cli_status_sessionId}: {info['session_id']}\n"
                    f"{Resources.cli_status_pid}: {info['pid']}\n{Resources.cli_status_mode}: {info['mode']}\n"
                    f"{Resources.cli_status_status}: {info['status']}\n{Resources.cli_status_unit}: {info['unit']}\n"
                    f"{Resources.cli_status_configs}: "
                    f"{', '.join(info['configs']) if info['configs'] else Resources.cli_status_none}\n"
                    f"{Resources.cli_status_progress}: {info['progress'][0]}/{info['progress'][1]}\n"
                    f"{Resources.cli_status_error}: {info['error']}")

        self.ok(Resources.cli_task_statusTitle, data, formatter=format_info)

    @staticmethod
    def _build_task_list_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description=Resources.cli_task_listDescription)

    @cmd2.as_subcommand_to("task", "list", _build_task_list_parser, help=Resources.cli_task_listDescription)
    def _task_list(self, _: argparse.Namespace) -> None:
        from SRACore.task import task_registry
        entries = sorted(task_registry.get_entries(), key=lambda e: (e.order, e.name))
        if not entries:
            self.err(Resources.cli_task_listEmpty)
            return
        items = [{"id": e.name, "order": e.order, "class": e.task_cls.__name__,
                      "doc": (e.task_cls.__doc__ or "").strip() or None} for e in entries]
        def format_item(_items: list[dict[str, str]]) -> str:
            str_buffer = [Resources.cli_task_listHeader]
            for i in _items:
                str_buffer.append(f" {i['order']}: {i['id']} # {i['doc'] or Resources.cli_task_listNoDescription}")
            return "\n".join(str_buffer)
        self.ok(Resources.cli_task_listRegistered(len(items)), items, formatter=format_item)

    @staticmethod
    def _build_task_reload_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description=Resources.cli_task_reloadDescription)

    @cmd2.as_subcommand_to("task", "reload", _build_task_reload_parser, help=Resources.cli_task_reloadDescription)
    def _task_reload(self, _: argparse.Namespace) -> None:
        from pathlib import Path

        from SRACore.task import task_registry

        if self.task_manager.is_thread_running():
            self.err(Resources.cli_task_reloadBusy)
            return

        package_dir = Path("tasks")
        if not package_dir.is_dir():
            self.err(Resources.cli_task_reloadNotFound(str(package_dir.resolve())))
            return

        before = set(task_registry.get_ids())
        task_registry.clear()

        reload_package("tasks")

        after = set(task_registry.get_ids())
        if not after:
            self.err(Resources.cli_task_reloadEmpty)
            return
        added = sorted(after - before)
        removed = sorted(before - after)
        message = Resources.cli_task_reloadSummary(len(after))
        if added:
            message += Resources.cli_task_reloadAdded(', '.join(added))
        if removed:
            message += Resources.cli_task_reloadRemoved(', '.join(removed))
        self.ok(message, {"tasks": task_registry.get_ids()})

    @staticmethod
    def _build_run_parser() -> cmd2.Cmd2ArgumentParser:
        run_parser = SRACli.cmd2argumentparser_factory(description=Text.assemble(Resources.run_description))
        run_parser.add_argument('config', nargs='*', help=Resources.run_configHelp)
        return run_parser

    @cmd2.with_argparser(_build_run_parser)
    def do_run(self, args: argparse.Namespace) -> None:
        """Run specified tasks, will block current command line until tasks complete"""
        self.ok(Resources.cli_run_started)
        try:
            self.task_manager.run_and_wait(*args.config)
        except KeyboardInterrupt:
            self.task_manager.request_stop()

    @staticmethod
    def _build_single_parser() -> cmd2.Cmd2ArgumentParser:
        single_parser = SRACli.cmd2argumentparser_factory(description=Text.assemble(Resources.single_description))
        single_parser.add_argument('task', help=Resources.single_taskHelp)
        single_parser.add_argument('--config', help=Resources.single_configHelp)
        return single_parser

    @cmd2.with_argparser(_build_single_parser)
    def do_single(self, args: argparse.Namespace) -> None:
        """Run a single specified task, will block current command line until task complete"""
        self.ok(Resources.cli_run_started)
        try:
            self.task_manager.run_task_and_wait(args.task, args.config)
        except KeyboardInterrupt:
            self.task_manager.request_stop()

    # endregion

    # region 扩展管理

    @staticmethod
    def _build_extension_parser() -> cmd2.Cmd2ArgumentParser:
        extension_parser = cmd2.Cmd2ArgumentParser(description=Resources.cli_extension_description)
        extension_parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return extension_parser

    @cmd2.with_argparser(_build_extension_parser)
    def do_extension(self, args: argparse.Namespace) -> None:
        args.cmd2_subcommand_func(args)

    @staticmethod
    def _build_extension_list_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description=Resources.cli_extension_listDescription)

    @cmd2.as_subcommand_to("extension", "list", _build_extension_list_parser, help=Resources.cli_extension_listDescription)
    def _extension_list(self, _: argparse.Namespace) -> None:
        data = self.context.extension_list()
        if not data:
            self.err(Resources.cli_extension_listEmpty)
            return

        def format_list(items):
            lines = [Resources.cli_extension_listHeader]
            for i in items:
                desc = f"  - {i['description']}" if i['description'] else ""
                config_str = f" (config: {i['config_class']})" if i['config_class'] else ""
                lines.append(f"  {i['id']} ({i['name']})  ->  {i['extension_class']}{config_str}{desc}")
            return "\n".join(lines)

        self.output(True, Resources.cli_extension_listRegistered(len(data)), data, formatter=format_list)

    @staticmethod
    def _build_extension_run_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description=Resources.cli_extension_runDescription)
        parser.add_argument('name', help=Resources.cli_extension_runNameHelp)
        parser.add_argument('--config', help=Resources.cli_extension_runConfigHelp)
        return parser

    @cmd2.as_subcommand_to("extension", "run", _build_extension_run_parser, help=Resources.cli_extension_runDescription)
    def _extension_run(self, args: argparse.Namespace) -> None:
        ok, message = self.context.extension_run(args.name, args.config)
        if ok:
            self.ok(message)
        else:
            self.err(message)

    @staticmethod
    def _build_extension_schema_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description=Resources.cli_extension_schemaDescription)
        parser.add_argument('name', help=Resources.cli_extension_schemaNameHelp)
        return parser

    @cmd2.as_subcommand_to("extension", "schema", _build_extension_schema_parser, help=Resources.cli_extension_schemaDescription)
    def _extension_schema(self, args: argparse.Namespace) -> None:
        schema = self.context.extension_schema(args.name)
        if schema is None:
            self.err(Resources.cli_extension_schemaNotFound(args.name))
            return
        self.ok(Resources.cli_extension_schemaTitle(args.name), schema, formatter=lambda s: json.dumps(s, ensure_ascii=False, indent=2))

    @staticmethod
    def _build_extension_reload_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description=Resources.cli_extension_reloadDescription)

    @cmd2.as_subcommand_to("extension", "reload", _build_extension_reload_parser,
                           help=Resources.cli_extension_reloadDescription)
    def _extension_reload(self, _: argparse.Namespace) -> None:
        ok, message = self.context.extension_reload()
        if not ok:
            self.err(message)
            return
        from SRACore.extension import extension_registry

        self.ok(message, {"extensions": sorted(extension_registry.get_ids())})

    @staticmethod
    def _build_extension_stop_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description=Resources.cli_extension_stopDescription)
        parser.add_argument('name', nargs='?', help=Resources.cli_extension_stopNameHelp)
        return parser

    @cmd2.as_subcommand_to("extension", "stop", _build_extension_stop_parser,
                           help=Resources.cli_extension_stopCurrentHelp)
    def _extension_stop(self, args: argparse.Namespace) -> None:
        if args.name:
            ok, message = self.context.extension_stop(args.name)
            if ok:
                self.ok(message)
            else:
                self.err(message)
            return

        if not self.extension_runner.is_thread_running():
            self.ok(Resources.cli_extension_stopNone)
            return
        self.extension_runner.stop_thread()
        self.ok(Resources.cli_extension_stopped)

    @staticmethod
    def _build_extension_status_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description=Resources.cli_extension_statusDescription)

    @cmd2.as_subcommand_to("extension", "status", _build_extension_status_parser, help=Resources.cli_extension_statusDescription)
    def _extension_status(self, _: argparse.Namespace) -> None:
        info = self.extension_runner.info
        data = {"status": info.status, "unit": info.unit, "error": info.error}
        self.ok(Resources.cli_extension_statusTitle, data,
                formatter=lambda d: f"{Resources.cli_status_status}: {d['status']}\n"
                                    f"{Resources.cli_status_unit}: {d['unit']}"
                + (f"\n{Resources.cli_status_error}: {d['error']}" if d['error'] else ""))

    @staticmethod
    def _build_extension_config_parser() -> cmd2.Cmd2ArgumentParser:
        parser = cmd2.Cmd2ArgumentParser(description=Resources.cli_extension_configDescription)
        parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return parser

    @staticmethod
    def _build_extension_config_get_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description=Resources.cli_extension_configGetDescription)
        parser.add_argument('name', help=Resources.cli_extension_configGetNameHelp)
        return parser

    @cmd2.as_subcommand_to("extension", "config", _build_extension_config_parser, help=Resources.cli_extension_configDescription)
    def _extension_config(self, args: argparse.Namespace) -> None:
        args.cmd2_subcommand_func(args)

    @cmd2.as_subcommand_to("extension config", "get", _build_extension_config_get_parser, help=Resources.cli_extension_configGetDescription)
    def _extension_config_get(self, args: argparse.Namespace) -> None:
        data = self.context.extension_config_get(args.name)
        if data is None:
            self.err(Resources.cli_extension_schemaNotFound(args.name))
            return
        self.ok(Resources.cli_extension_configGetTitle(args.name), data, formatter=lambda x: '\n'.join(f"  {key}: {value}" for key, value in x.items()))

    @staticmethod
    def _build_extension_config_set_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description=Resources.cli_extension_configSetDescription)
        parser.add_argument('name', help=Resources.cli_extension_configSetNameHelp)
        parser.add_argument('json', help=Resources.cli_extension_configSetJsonHelp)
        return parser

    @cmd2.as_subcommand_to("extension config", "set", _build_extension_config_set_parser, help=Resources.cli_extension_configSetDescription)
    def _extension_config_set(self, args: argparse.Namespace) -> None:
        try:
            data = json.loads(args.json)
        except json.JSONDecodeError as e:
            self.err(Resources.cli_extension_configSetJsonError(str(e)))
            return
        ok, message = self.context.extension_config_set(args.name, data)
        if ok:
            self.ok(message)
        else:
            self.err(message)

    # endregion

    # region Operator 统一调用

    @staticmethod
    def _build_operator_parser() -> cmd2.Cmd2ArgumentParser:
        description = Text.assemble(Resources.cli_operator_description)
        parser = cmd2.Cmd2ArgumentParser(description=description)
        parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return parser

    @cmd2.with_argparser(_build_operator_parser())
    def do_operator(self, args: argparse.Namespace) -> None:
        args.cmd2_subcommand_func(args)

    @staticmethod
    def _build_operator_list_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description=Resources.cli_operator_listDescription)

    @cmd2.as_subcommand_to("operator", "list", _build_operator_list_parser,
                           help=Resources.cli_operator_listDescription)
    def _operator_list(self, _: argparse.Namespace) -> None:
        from SRACore.operators.ioperator import IOperator

        methods = self.context.operator_list()

        def format_methods(_methods: list[str]) -> str:
            lines = [Resources.cli_operator_listHeader]
            for name in _methods:
                doc = getattr(IOperator, name).__doc__
                summary = (doc.split("\n")[0].strip() if doc else "")
                lines.append(f"  {name:20s} {summary}")
            return "\n".join(lines)

        self.ok(Resources.cli_operator_listTitle, methods, formatter=format_methods)

    @staticmethod
    def _build_operator_help_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description=Resources.cli_operator_helpDescription)
        parser.add_argument('method', help=Resources.cli_operator_methodHelp)
        return parser

    @cmd2.as_subcommand_to("operator", "help", _build_operator_help_parser,
                           help=Resources.cli_operator_helpDescription)
    def _operator_help(self, args: argparse.Namespace) -> None:
        data = self.context.operator_help(args.method)
        if data is None:
            self.err(Resources.cli_operator_helpNotFound(args.method))
            return
        self.ok(args.method, data)

    @staticmethod
    def _build_operator_call_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description=Resources.cli_operator_callDescription)
        parser.add_argument('method', help=Resources.cli_operator_callMethodHelp)
        parser.add_argument('params', nargs='?', default='{}',
                            help=Resources.cli_operator_callParamsHelp)
        return parser

    @cmd2.as_subcommand_to("operator", "call", _build_operator_call_parser,
                           help=Resources.cli_operator_callDescription)
    def _operator_call(self, args: argparse.Namespace) -> None:
        # 解析 JSON 参数
        try:
            params: dict[str, object] = json.loads(args.params)
        except json.JSONDecodeError as e:
            self.err(Resources.cli_operator_callJsonError(str(e)))
            return

        ok, message, data = self.context.operator_call(args.method, params)
        if ok:
            self.ok(message, data)
        else:
            self.err(message)

    # endregion

    # region 其他命令
    def do_init(self, _: str):
        """Initialize the application: download resources and create default settings/config."""
        import io
        import os
        import zipfile
        from urllib.error import URLError, HTTPError
        from urllib.request import Request, urlopen

        from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TransferSpeedColumn

        from SRACore.models.tasks_config import TasksConfig
        from SRACore.util.const import AppDataDir, ConfigsDir

        def download(url: str) -> bytes:
            """流式下载文件并显示进度条，返回完整内容。"""
            req = Request(url, headers={"User-Agent": "SRA-cli"})
            with urlopen(req) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                progress = Progress(
                    TextColumn("{task.description}"),
                    BarColumn(),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                )
                with progress:
                    task = progress.add_task(url.rsplit("/", 1)[-1], total=total or None)
                    chunks: list[bytes] = []
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        chunks.append(chunk)
                        progress.advance(task, len(chunk))
                return b"".join(chunks)

        # R2 资源站：固定文件名区分正式版/beta（版本含 "-" 视为 beta），避免 beta 覆盖正式版包
        beta = "_beta" if "-" in VERSION else ""
        packages = [
            f"SRAFrontend_WebUI{beta}.zip",
            f"StarRailAssistant_Resources{beta}.zip",
        ]
        base_url = "https://resource.starrailassistant.top"
        cwd = os.getcwd()
        for package_name in packages:
            url = f"{base_url}/{package_name}"
            self.ok(f"Downloading {url} ...")
            try:
                data = download(url)
            except (URLError, HTTPError) as e:
                self.err(f"Failed to download {package_name}: {e}")
                return True

            self.ok(f"Extracting {package_name} ...")
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                # 跳过包内 MD5 清单：它是整包（Core / Full / Lite）的完整性清单，
                # WebUI / 资源包若带同名清单会覆盖目标目录的 manifest.md5.json，
                # 导致完整性校验与更新后的冗余文件清理误判（含已发布的历史包）
                for member in zf.infolist():
                    if member.filename.replace("\\", "/").rsplit("/", 1)[-1] == "manifest.md5.json":
                        continue
                    zf.extract(member, cwd)
            self.ok(f"{package_name} extracted to {cwd}")

        # 创建设置文件
        AppDataDir.mkdir(parents=True, exist_ok=True)
        self.settings.settings.Advanced.isDeveloperModeEnabled = True
        self.settings.settings.Advanced.isCustomBackendEnabled = True
        # 发布包内为内嵌运行时 python/python.exe；pip/uv 安装环境没有该文件，
        # 回退到 console script sra-cli（随包分发时该命令并不存在）
        bundled_python = os.path.join(cwd, "python", "python.exe")
        if os.path.isfile(bundled_python):
            self.settings.settings.Advanced.customBackendCommand = bundled_python
            self.settings.settings.Advanced.customBackendArguments = "main.py"
        else:
            self.settings.settings.Advanced.customBackendCommand = "sra-cli"
            self.settings.settings.Advanced.customBackendArguments = ""
        self.settings.settings.Advanced.customBackendWorkingDirectory = cwd
        self.settings.save_settings()
        self.ok(f"Created/Updated settings file: {SettingsJson}")

        # 创建默认配置文件
        ConfigsDir.mkdir(parents=True, exist_ok=True)
        config_path = ConfigsDir / "Default.json"
        if not config_path.exists():
            config = TasksConfig.from_dict({"name": "Default"})
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            self.ok(f"Created default config: {config_path}")
        else:
            self.ok(f"Default config already exists: {config_path}")

        self.ok(Resources.cli_initCompleted)
        return True

    def do_version(self, _: str):
        """Show version information"""
        self.ok(Resources.cli_versionTitle, VERSION)

    def do_quit(self, _) -> bool | None:
        """Exit this application."""
        self._cleanup()
        # Return True to stop the command loop
        self.last_result = True
        return True

    do_exit = do_quit

    def do_notify(self, arg: str):
        """Notification command - support test email/webhook/telegram/serverchan/onebot notification"""
        args = arg.split()
        if not args:
            self.err(Resources.cli_invalidArguments('notify'))
            return

        command = args[0]
        if command == 'test' and len(args) >= 2:
            channel = args[1]
            from SRACore.notification import send_channel_test_notification

            label, result = send_channel_test_notification(channel, self.settings.settings.Notification)
            if label:
                msg = label + "测试通知发送" + ("成功" if result else "失败")
                if result:
                    self.ok(msg)
                else:
                    self.err(msg)
            else:
                self.err(Resources.cli_invalidArguments("notify"))
        else:
            self.err(Resources.cli_invalidArguments('notify'))

    # endregion

    # region 生命周期管理

    def _cleanup(self):
        """清理资源：停止运行中的工作并释放全局键盘监听"""
        self.context.shutdown()

    # endregion
    @staticmethod
    def cmd2argumentparser_factory(**kwargs) -> cmd2.Cmd2ArgumentParser:
        parser = cmd2.Cmd2ArgumentParser(**kwargs)
        parser.add_argument('--json', action='store_true', help=Resources.cli_jsonHelp)
        return parser

    def output(self,
               success: bool,
               message: str,
               data=None,
               serializer: Callable[[Any], Any] | None = None,
               formatter: Callable[[Any], str] | None = None):
        """统一输出结果，对齐 HTTP 响应 R(success, message, data)

        JSON 模式由 precmd 自动检测 --json 参数设置 self._use_json
        """
        if self._use_json:
            response = {"success": success, "message": message}
            if data is not None:
                response["data"] = data
            self.poutput(json.dumps(response, default=serializer))
        else:
            prefix = "[OK]" if success else "[FAIL]"
            self.poutput(f"{prefix} {message}", highlight=True)
            if data is not None:
                self.poutput("\n".join((formatter(data) if formatter else str(data)).split("\n")), highlight=True)

    def ok(self, message: str, data=None,
           serializer: Callable[[Any], Any] | None = None,
           formatter: Callable[[Any], str] | None = None):
        """输出成功结果"""
        self.output(True, message, data, serializer, formatter)

    def err(self, message: str):
        """输出错误结果"""
        self.output(False, message)
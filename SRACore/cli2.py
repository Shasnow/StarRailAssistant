import argparse
import dataclasses
import json
from collections.abc import Callable
from typing import Any
import typing

import cmd2
from loguru import logger
from rich.text import Text

from SRACore.extension import ExtensionConfigManager, ExtensionRunner, load_extensions
from SRACore.localization import Resource
from SRACore.models.app_settings import AppSettings
from SRACore.operators.factory import OperatorFactory, OperatorType
from SRACore.runtime.event_listener import KeyboardListener
from SRACore.service.setting_service import SettingsService
from SRACore.thread.task_process import TaskManager
from SRACore.util.const import VERSION, CORE


class SRACli(cmd2.Cmd):
    DEFAULT_CATEGORY = "Build-in Commands"

    def __init__(self, settings_service: SettingsService):
        super().__init__(startup_script=".srarc",
                         auto_load_commands=True)
        self.intro = f"Welcome to SRA-cli (version {VERSION}, core {CORE}). \nType 'help' to list commands."
        self.prompt = 'sra> '
        self.default_error = Resource.cli_defaultError
        self.settings_service = settings_service
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
        # 初始化任务管理器
        self.task_manager = TaskManager(settings_service)

        # 初始化扩展系统：动态导入扩展模块并创建运行器
        load_extensions()
        self.extension_config_manager = ExtensionConfigManager()
        self.extension_runner = ExtensionRunner(
            self.extension_config_manager, settings_service)

        # 初始化键盘监听器
        stop_hotkey = settings_service.settings.General.hotkeyStop.lower() or 'f9'
        self.event_listener = KeyboardListener()
        self.event_listener.register_key_event(stop_hotkey, self._task_stop)
        self.event_listener.start()

    def precmd(self, statement: cmd2.Statement | str) -> cmd2.Statement:
        """在执行命令前检查是否需要使用 JSON 输出"""
        self._use_json = '--json' in getattr(statement, 'raw', statement)
        return super().precmd(statement)

    # region 任务管理
    @staticmethod
    def _build_task_parser() -> cmd2.Cmd2ArgumentParser:
        task_description = Text.assemble(Resource.task_description)
        task_parser = cmd2.Cmd2ArgumentParser(description=task_description)
        task_parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return task_parser

    @cmd2.with_argparser(_build_task_parser, preserve_quotes=True)
    def do_task(self, args: argparse.Namespace) -> None:
        args.cmd2_subcommand_func(args)

    @staticmethod
    def _build_task_run_parser() -> cmd2.Cmd2ArgumentParser:
        task_run_parser = SRACli.cmd2argumentparser_factory(description=Text.assemble(Resource.run_description))
        task_run_parser.add_argument('config', nargs='*', help=Resource.run_configHelp)
        return task_run_parser

    @cmd2.as_subcommand_to("task", "run", _build_task_run_parser, help=Resource.run_description)
    def _task_run(self, args: argparse.Namespace) -> None:
        if self.task_manager.is_thread_running():
            self.err(Resource.cli_task_taskAlreadyRunning)
            return
        self.task_manager.run_in_thread(*args.config)

    @staticmethod
    def _build_task_single_parser() -> cmd2.Cmd2ArgumentParser:
        task_single_parser = SRACli.cmd2argumentparser_factory(description=Text.assemble(Resource.single_description))
        task_single_parser.add_argument('task', help=Resource.single_taskHelp)
        task_single_parser.add_argument('--config', help=Resource.single_configHelp)
        return task_single_parser

    @cmd2.as_subcommand_to("task", "single", _build_task_single_parser, help=Resource.single_description)
    def _task_single(self, args: argparse.Namespace) -> None:
        if self.task_manager.is_thread_running():
            self.err(Resource.cli_task_taskAlreadyRunning)
            return
        if self.task_manager.run_task_in_thread(args.task, args.config):
            self.ok(Resource.cli_run_started)

    @staticmethod
    def _build_task_stop_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description=Text.assemble(Resource.stop_description))

    @cmd2.as_subcommand_to("task", "stop", _build_task_stop_parser, help=Resource.stop_description)
    def _task_stop(self, _) -> None:
        if self.task_manager.is_thread_running():
            self.task_manager.stop_thread()
        else:
            logger.info(Resource.cli_task_notRunning)

    @staticmethod
    def _build_task_status_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description="Show current task status")

    @cmd2.as_subcommand_to("task", "status", _build_task_status_parser, help="Show current task status")
    def _task_status(self, _: argparse.Namespace) -> None:
        if typing.TYPE_CHECKING:
            from SRACore.thread.runner import RuntimeInfo

        def format_info(info: 'RuntimeInfo') -> str:
            return (f"Session ID: {info.session_id}\n"
                    f"PID: {info.pid}\nMode: {info.mode}\n"
                    f"Status: {info.status}\nUnit: {info.unit}\n"
                    f"Configs: {', '.join(info.configs) if info.configs else 'N/A'}\n"
                    f"Progress: {info.progress[0]}/{info.progress[1]}\nError: {info.error}")

        self.ok("Task status", self.task_manager.info, serializer=dataclasses.asdict, formatter=format_info)

    @staticmethod
    def _build_task_list_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description="List all registered tasks")

    @cmd2.as_subcommand_to("task", "list", _build_task_list_parser, help="List all registered tasks")
    def _task_list(self, _: argparse.Namespace) -> None:
        from SRACore.task import task_registry
        entries = sorted(task_registry.get_entries(), key=lambda e: (e.order, e.name))
        if not entries:
            self.err("没有已注册的任务")
            return
        items = [{"id": e.name, "order": e.order, "class": e.task_cls.__name__,
                      "doc": (e.task_cls.__doc__ or "").strip() or None} for e in entries]
        def format_item(_items: list[dict[str, str]]) -> str:
            str_buffer = ["可用任务:"]
            for i in _items:
                str_buffer.append(f" {i['order']}: {i['id']} # {i['doc'] or 'No description'}")
            return "\n".join(str_buffer)
        self.ok(f"已注册 {len(items)} 个任务", items, formatter=format_item)

    @staticmethod
    def _build_run_parser() -> cmd2.Cmd2ArgumentParser:
        run_parser = SRACli.cmd2argumentparser_factory(description=Text.assemble(Resource.run_description))
        run_parser.add_argument('config', nargs='*', help=Resource.run_configHelp)
        return run_parser

    @cmd2.with_argparser(_build_run_parser)
    def do_run(self, args: argparse.Namespace) -> None:
        """Run specified tasks, will block current command line until tasks complete"""
        self.ok(Resource.cli_run_started)
        try:
            self.task_manager.run_and_wait(*args.config)
        except KeyboardInterrupt:
            self.task_manager.request_stop()

    @staticmethod
    def _build_single_parser() -> cmd2.Cmd2ArgumentParser:
        single_parser = SRACli.cmd2argumentparser_factory(description=Text.assemble(Resource.single_description))
        single_parser.add_argument('task', help=Resource.single_taskHelp)
        single_parser.add_argument('--config', help=Resource.single_configHelp)
        return single_parser

    @cmd2.with_argparser(_build_single_parser)
    def do_single(self, args: argparse.Namespace) -> None:
        """Run a single specified task, will block current command line until task complete"""
        self.ok(Resource.cli_run_started)
        try:
            self.task_manager.run_task_and_wait(args.task, args.config)
        except KeyboardInterrupt:
            self.task_manager.request_stop()

    # endregion

    # region 扩展管理

    @staticmethod
    def _build_extension_parser() -> cmd2.Cmd2ArgumentParser:
        extension_parser = cmd2.Cmd2ArgumentParser(description="扩展管理：查看、运行已注册的扩展")
        extension_parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return extension_parser

    @cmd2.with_argparser(_build_extension_parser)
    def do_extension(self, args: argparse.Namespace) -> None:
        args.cmd2_subcommand_func(args)

    @staticmethod
    def _build_extension_list_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description="列出所有已注册的扩展")

    @cmd2.as_subcommand_to("extension", "list", _build_extension_list_parser, help="列出所有已注册的扩展")
    def _extension_list(self, _: argparse.Namespace) -> None:
        from SRACore.extension import extension_registry

        ids = extension_registry.get_ids()
        if not ids:
            self.err("没有已注册的扩展")
            return

        data = []
        for ext_id in ids:
            entry = extension_registry.get(ext_id)
            data.append({
                "id": ext_id, "name": entry.name, "description": entry.description,
                "extension_class": entry.extension_cls.__name__,
                "config_class": entry.config_cls.__name__ if entry.config_cls else "",
            })

        def format_list(items):
            lines = ["扩展："]
            for i in items:
                desc = f"  - {i['description']}" if i['description'] else ""
                config_str = f" (config: {i['config_class']})" if i['config_class'] else ""
                lines.append(f"  {i['id']} ({i['name']})  ->  {i['extension_class']}{config_str}{desc}")
            return "\n".join(lines)

        self.output(True, f"已注册 {len(data)} 个扩展", data, formatter=format_list)

    @staticmethod
    def _build_extension_run_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description="按扩展类型自动分发：非后台扩展走共享线程，后台扩展走专用线程")
        parser.add_argument('name', help="扩展标识（可通过 extension list 查看）")
        parser.add_argument('--config', help="扩展配置文件名（不带 .json 后缀），不指定则不加载文件配置")
        return parser

    @cmd2.as_subcommand_to("extension", "run", _build_extension_run_parser, help="运行指定的扩展")
    def _extension_run(self, args: argparse.Namespace) -> None:
        from SRACore.extension import extension_registry

        if not extension_registry.has_id(args.name):
            self.err(f"扩展 '{args.name}' 不存在，使用 'extension list' 查看可用扩展")
            return
        if args.config:
            self.extension_config_manager.load(args.config)

        if extension_registry.is_background(args.name):
            ok = self.extension_runner.start_extension(args.name)
            if ok:
                self.ok(f"已启动后台扩展 '{args.name}'")
            else:
                self.err(f"无法启动后台扩展 '{args.name}'")
            return

        result = self.extension_runner.run_in_thread(args.name)
        if result:
            self.ok(f"已启动扩展 '{args.name}'")
        else:
            self.err(f"无法启动扩展 '{args.name}'")

    @staticmethod
    def _build_extension_schema_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description="显示扩展的配置 Schema 详情")
        parser.add_argument('name', help="扩展键名")
        return parser

    @cmd2.as_subcommand_to("extension", "schema", _build_extension_schema_parser, help="显示扩展的配置 Schema 详情")
    def _extension_schema(self, args: argparse.Namespace) -> None:
        from SRACore.extension import extension_registry

        if not extension_registry.has_id(args.name):
            self.err(f"扩展 '{args.name}' 不存在")
            return
        schema = extension_registry.get_schema(args.name)

        self.ok(f"扩展 {args.name} 配置模式", schema, formatter=lambda s:json.dumps(s, ensure_ascii=False, indent=2))

    @staticmethod
    def _build_extension_reload_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description="重新扫描并导入扩展模块")

    @cmd2.as_subcommand_to("extension", "reload", _build_extension_reload_parser, help="重新扫描并导入扩展模块")
    def _extension_reload(self, _: argparse.Namespace) -> None:
        from SRACore.extension import extension_registry

        before = set(extension_registry.get_ids())
        load_extensions()
        after = set(extension_registry.get_ids())
        added = after - before
        if added:
            self.ok(f"新增扩展: {', '.join(added)}", len(after))
        else:
            self.ok("未发现新扩展", len(after))

    @staticmethod
    def _build_extension_stop_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description="停止指定的后台扩展或当前正在运行的单次扩展")
        parser.add_argument('name', nargs='?', help="扩展标识；若不传则停止当前单次扩展")
        return parser

    @cmd2.as_subcommand_to("extension", "stop", _build_extension_stop_parser,
                           help="停止指定后台扩展或当前正在运行的单次扩展")
    def _extension_stop(self, args: argparse.Namespace) -> None:
        if args.name:
            from SRACore.extension import extension_registry

            if not extension_registry.has_id(args.name):
                self.err(f"扩展 '{args.name}' 不存在")
                return
            if not extension_registry.is_background(args.name):
                self.err(f"扩展 '{args.name}' 不是后台扩展，不能通过 stop 指定停止")
                return
            stopped = self.extension_runner.stop_extension(args.name)
            self.ok(f"已停止后台扩展 '{args.name}'" if stopped else f"后台扩展 '{args.name}' 未运行")
            return

        if not self.extension_runner.is_thread_running():
            self.ok("当前没有正在运行的扩展")
            return
        self.extension_runner.stop_thread()
        self.ok("扩展已停止")

    @staticmethod
    def _build_extension_status_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description="显示扩展运行状态")

    @cmd2.as_subcommand_to("extension", "status", _build_extension_status_parser, help="显示扩展运行状态")
    def _extension_status(self, _: argparse.Namespace) -> None:
        info = self.extension_runner.info
        data = {"status": info.status, "unit": info.unit, "error": info.error}
        self.ok("Extension status", data,
                formatter=lambda d: f"Status: {d['status']}\nUnit: {d['unit']}"
                + (f"\nError: {d['error']}" if d['error'] else ""))

    @staticmethod
    def _build_extension_config_parser() -> cmd2.Cmd2ArgumentParser:
        parser = cmd2.Cmd2ArgumentParser(description="扩展配置管理")
        parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return parser

    @staticmethod
    def _build_extension_config_get_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description="获取扩展配置")
        parser.add_argument('name', help="扩展标识")
        return parser

    @cmd2.as_subcommand_to("extension", "config", _build_extension_config_parser, help="扩展配置管理")
    def _extension_config(self, args: argparse.Namespace) -> None:
        args.cmd2_subcommand_func(args)

    @cmd2.as_subcommand_to("extension config", "get", _build_extension_config_get_parser, help="获取扩展配置")
    def _extension_config_get(self, args: argparse.Namespace) -> None:
        from SRACore.extension import extension_registry

        if not extension_registry.has_id(args.name):
            self.err(f"扩展 '{args.name}' 不存在")
            return
        config = self.extension_config_manager.get(args.name)
        if config is None:
            self.ok("配置为空")
            return
        data = config.model_dump(by_alias=True)
        self.ok(f"扩展 {args.name} 配置", data, formatter=lambda x: '\n'.join(f"  {key}: {value}" for key, value in x.items()))

    @staticmethod
    def _build_extension_config_set_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description="设置扩展配置")
        parser.add_argument('name', help="扩展标识")
        parser.add_argument('json', help="配置 JSON 字符串")
        return parser

    @cmd2.as_subcommand_to("extension config", "set", _build_extension_config_set_parser, help="设置扩展配置")
    def _extension_config_set(self, args: argparse.Namespace) -> None:
        from SRACore.extension import extension_registry

        if not extension_registry.has_id(args.name):
            self.err(f"扩展 '{args.name}' 不存在")
            return
        try:
            data = json.loads(args.json)
        except json.JSONDecodeError as e:
            self.err(f"JSON 格式错误: {e}")
            return
        config_cls = extension_registry.get_config_class(args.name)
        if config_cls is None:
            self.err(f"扩展 '{args.name}' 没有配置")
            return
        try:
            config = config_cls.model_validate(data, by_alias=True)
        except Exception as e:
            self.err(f"配置验证失败: {e}")
            return
        self.extension_config_manager.set(args.name, config)
        self.extension_config_manager.save()
        self.ok(f"扩展 {args.name} 配置已保存")

    # endregion

    # region Operator 统一调用

    # 不需要暴露给用户的方法（内部/静态/构造器）
    _OP_EXCLUDE = frozenset({"__init__", "sleep", "do_while", "wait_any", "login"})

    @staticmethod
    def _build_operator_parser() -> cmd2.Cmd2ArgumentParser:
        description = Text.assemble("统一调用 Operator 方法，与游戏交互")
        parser = cmd2.Cmd2ArgumentParser(description=description)
        parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return parser

    @cmd2.with_argparser(_build_operator_parser())
    def do_operator(self, args: argparse.Namespace) -> None:
        args.cmd2_subcommand_func(args)

    @staticmethod
    def _get_op_methods() -> list[str]:
        """获取 IOperator 上所有可调用的公共方法名"""
        import inspect
        from SRACore.operators.ioperator import IOperator
        return sorted(
            name for name, _ in inspect.getmembers(IOperator, predicate=inspect.isfunction)
            if not name.startswith("_") and name not in SRACli._OP_EXCLUDE
        )

    @staticmethod
    def _build_operator_list_parser() -> cmd2.Cmd2ArgumentParser:
        return SRACli.cmd2argumentparser_factory(description="列出所有可用的 Operator 方法")

    @cmd2.as_subcommand_to("operator", "list", _build_operator_list_parser,
                           help="列出所有可用的 Operator 方法")
    def _operator_list(self, _: argparse.Namespace) -> None:
        from SRACore.operators.ioperator import IOperator

        methods = self._get_op_methods()

        def format_methods(_methods: list[str]) -> str:
            lines = ["可用方法:"]
            for name in _methods:
                doc = getattr(IOperator, name).__doc__
                summary = (doc.split("\n")[0].strip() if doc else "")
                lines.append(f"  {name:20s} {summary}")
            return "\n".join(lines)

        self.ok("Operator methods", methods, formatter=format_methods)

    @staticmethod
    def _build_operator_help_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description="获取 Operator 方法的详细帮助")
        parser.add_argument('method', help="方法名称")
        return parser

    @cmd2.as_subcommand_to("operator", "help", _build_operator_help_parser,
                           help="获取 Operator 方法的详细帮助")
    def _operator_help(self, args: argparse.Namespace) -> None:
        import inspect

        from SRACore.operators.ioperator import IOperator

        method_name: str = args.method
        method = getattr(IOperator, method_name, None)
        if method is None or not callable(method):
            self.err(f"方法 '{method_name}' 不存在")
            return

        sig = inspect.signature(method)
        params = []
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            info = {"name": name}
            if param.default is not inspect.Parameter.empty:
                info["default"] = param.default
            if param.annotation is not inspect.Parameter.empty:
                info["type"] = str(param.annotation)
            params.append(info)

        doc = (method.__doc__ or "").strip()
        summary = doc.split("\n")[0] if doc else ""

        self.ok(method_name, {
            "method": method_name,
            "summary": summary, "parameters": params, "doc": doc,
        })

    @staticmethod
    def _build_operator_call_parser() -> cmd2.Cmd2ArgumentParser:
        parser = SRACli.cmd2argumentparser_factory(description="调用指定的 Operator 方法")
        parser.add_argument('method', help="方法名称（可通过 operator list 查看）")
        parser.add_argument('params', nargs='?', default='{}',
                            help="JSON 格式的方法参数，例如 '{\"x\": 0.5, \"y\": 0.7}'")
        return parser

    @cmd2.as_subcommand_to("operator", "call", _build_operator_call_parser,
                           help="调用 Operator 方法")
    def _operator_call(self, args: argparse.Namespace) -> None:
        import inspect

        method_name: str = args.method

        # 创建 Operator 实例，从实例获取实际方法（而非抽象类上的空方法）
        try:
            optype = (OperatorType.Browser
                      if self.settings_service.settings.General.isCloudGameEnabled
                      else OperatorType.Local)
            op = OperatorFactory.get_operator(optype, self.settings_service.settings)
        except Exception as e:
            self.err(f"Operator 初始化失败: {e}")
            return

        method = getattr(op, method_name, None)
        if method is None or not callable(method):
            self.err(f"方法 '{method_name}' 不存在。可用方法: {', '.join(self._get_op_methods())}")
            return

        # 解析 JSON 参数
        try:
            params: dict[str, object] = json.loads(args.params)
        except json.JSONDecodeError as e:
            self.err(f"JSON 解析错误: {e}")
            return

        def _serialize_result(res):
            """通用序列化：将 Box、Image 等特殊类型转为可 JSON 化的 dict"""
            from PIL.Image import Image as PILImage
            if isinstance(res, PILImage):
                path = params.get("save_path")
                return {"path": path, "width": res.width, "height": res.height}
            return res

        try:
            sig = inspect.signature(method)
            bound = sig.bind(**params)
            bound.apply_defaults()
            # noinspection calling-non-callable
            result = method(*bound.args, **bound.kwargs)

            serialized = _serialize_result(result)
            self.ok(f"{method_name} 执行成功", serialized)

        except FileNotFoundError as e:
            self.err(f"文件未找到: {e}")
        except KeyError as e:
            self.err(f"缺少必需参数: {e}")
        except TypeError as e:
            self.err(f"参数类型错误: {e}")
        except Exception as e:
            self.err(f"执行失败: {e}")

    # endregion

    # region 其他命令
    def do_init(self, _: str):
        """Initialize the application: download resources and create default settings/config."""
        import io
        import os
        import zipfile
        from urllib.error import URLError, HTTPError
        from urllib.request import Request, urlopen

        from SRACore.models.tasks_config import TasksConfig
        from SRACore.util.const import AppDataDir, ConfigsDir

        url = f"https://github.com/Shasnow/StarRailAssistant/releases/download/v{VERSION}/StarRailAssistant_Resources_v{VERSION}.zip"
        # url = f"https://download.auto-mas.top/d/StarRailAssistant/StarRailAssistant_Resource_v{VERSION}.zip"
        self.ok(f"Downloading resources from {url} ...")
        try:
            req = Request(url, headers={"User-Agent": "SRA-cli"})
            with urlopen(req) as resp:
                data = resp.read()
        except (URLError, HTTPError) as e:
            self.err(f"Failed to download resources: {e}")
            return True

        self.ok("Extracting resources ...")
        cwd = os.getcwd()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(cwd)
        self.ok(f"Resources extracted to {cwd}")

        # 创建设置文件
        AppDataDir.mkdir(parents=True, exist_ok=True)
        settings_path = AppDataDir / "settings.json"
        if not settings_path.exists():
            settings = AppSettings.from_dict({})
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings.to_dict(), f, indent=2, ensure_ascii=False)
            self.ok(f"Created settings file: {settings_path}")
        else:
            self.ok(f"Settings file already exists: {settings_path}")

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

        self.ok("Initialization completed.")
        return True

    def do_version(self, _: str):
        """Show version information"""
        self.ok("Version", VERSION)

    def do_quit(self, _: argparse.Namespace) -> bool | None:
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
            self.err(Resource.cli_invalidArguments('notify'))
            return

        command = args[0]
        if command == 'test' and len(args) >= 2:
            channel = args[1]
            from SRACore.notification import send_channel_test_notification

            label, result = send_channel_test_notification(channel, self.settings_service.settings.Notification)
            if label:
                msg = label + "测试通知发送" + ("成功" if result else "失败")
                if result:
                    self.ok(msg)
                else:
                    self.err(msg)
            else:
                self.err(Resource.cli_invalidArguments("notify"))
        else:
            self.err(Resource.cli_invalidArguments('notify'))

    # endregion

    # region 生命周期管理

    def _cleanup(self):
        """清理资源"""
        self.task_manager.stop_thread(timeout=5.0)
        self.extension_runner.stop_thread(timeout=5.0)
        self.event_listener.stop()

    # endregion
    @staticmethod
    def cmd2argumentparser_factory(**kwargs) -> cmd2.Cmd2ArgumentParser:
        parser = cmd2.Cmd2ArgumentParser(**kwargs)
        parser.add_argument('--json', action='store_true', help='Output JSON instead of plain text')
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
                self.poutput(formatter(data) if formatter else str(data), highlight=True)

    def ok(self, message: str, data=None,
           serializer: Callable[[Any], Any] | None = None,
           formatter: Callable[[Any], str] | None = None):
        """输出成功结果"""
        self.output(True, message, data, serializer, formatter)

    def err(self, message: str):
        """输出错误结果"""
        self.output(False, message)

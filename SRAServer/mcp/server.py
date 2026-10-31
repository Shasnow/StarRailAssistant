"""MCP 工具端点：27 个 ``sra_*`` 工具 + Streamable HTTP ASGI 应用。

工具名称、描述与参数默认值逐条对齐 ``McpController.cs``；实现直接调用
进程内的 :class:`~SRAServer.context.ServerContext` 与各 service，不再经 CLI 子进程。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ImageContent, TextContent

from SRACore.util.const import VERSION

from SRAServer.schemas.envelope import R

_NO_RESPONSE_MSG = "(No response from backend, is the backend running?)"
_OCR_COORD_NOTE = "Coordinates are in 1080p game window pixels."
_SCREENSHOT_NOTE = "You must convert coordinates from 720p to 1080p if you want to use them in other tools."


def _dump(payload: Any) -> str:
    """按 Web 风格序列化对象（保序、中文不转义）。"""
    return json.dumps(payload, ensure_ascii=False, default=str)


def _valid_method_name(method: str) -> bool:
    """方法名仅允许 ASCII 字母数字与下划线（对齐 C# IsValidMethodName）。"""
    return bool(method) and all(ch.isascii() and (ch.isalnum() or ch == "_") for ch in method)


def build_mcp_server(core) -> MCPServer:  # core: SRAServer.context.ServerContext
    """构造并注册全部 MCP 工具（闭包持有 ServerContext）。"""
    mcp = MCPServer("SRA Server", version=VERSION)

    # ── 截图与后端控制 ──

    @mcp.tool(name="sra_screenshot", description="Take a screenshot(720p) of the game window(1080p)")
    async def take_screenshot() -> list[Any]:
        _message, data = await asyncio.to_thread(core.backend.screenshot)
        if not data:
            return [TextContent(type="text", text="Failed to take screenshot from backend.")]
        return [
            ImageContent(type="image", data=_b64(data), mimeType="image/jpeg"),
            TextContent(type="text", text=_SCREENSHOT_NOTE),
        ]

    @mcp.tool(name="sra_startup", description="Start StarRailAssistant Backend")
    async def start_backend() -> str:
        # 服务进程内即后端，启动为幂等操作
        return "StarRailAssistant Backend started successfully."

    @mcp.tool(name="sra_shutdown", description="Shutdown StarRailAssistant Backend")
    async def shutdown_backend() -> str:
        await asyncio.to_thread(core.backend.stop)
        return "StarRailAssistant Backend shutdown successfully."

    @mcp.tool(name="sra_restart", description="Restart StarRailAssistant Backend")
    async def restart_backend() -> str:
        try:
            await asyncio.to_thread(core.backend.restart)
        except Exception:
            return "Failed to restart StarRailAssistant Backend (executable not found or launch error)."
        return "StarRailAssistant Backend restarted successfully."

    # ── 任务 ──

    @mcp.tool(name="sra_task_list", description="List all available tasks")
    async def list_tasks() -> str:
        from SRACore.task import task_registry

        entries = sorted(task_registry.get_entries(), key=lambda e: (e.order, e.name))
        items = [
            {
                "id": e.name,
                "order": e.order,
                "class": e.task_cls.__name__,
                "doc": (e.task_cls.__doc__ or "").strip() or None,
            }
            for e in entries
        ]
        return _dump(R(True, f"已注册 {len(items)} 个任务", items))

    @mcp.tool(name="sra_task_run", description="Run all selected tasks in given config(s)")
    async def run_tasks(configNames: str | None = None) -> str:
        names = configNames.split() if configNames else []
        started = await asyncio.to_thread(core.run_configs, names)
        if started:
            return "Successfully started tasks. Check the task status or logs for progress."
        return "Failed to start tasks."

    @mcp.tool(name="sra_task_single", description="Run a single task by name or index")
    async def run_single_task(task: str, configName: str | None = None) -> str:
        started = await asyncio.to_thread(core.run_single, task, configName or None)
        if started:
            return f"Successfully started task '{task}'. Check the task status or logs for progress."
        return f"Failed to start task '{task}'."

    @mcp.tool(name="sra_task_stop", description="Stop the currently running task")
    async def stop_task() -> str:
        if not core.is_busy():
            return "Failed to send stop signal. No task may be running."
        await asyncio.to_thread(core.stop_running_work)
        return "Successfully sent stop signal to the running task."

    @mcp.tool(name="sra_task_status", description="Get the status of the currently running task")
    async def task_status() -> str:
        return _dump(R(True, "Task status", core.task_status()))

    # ── Operator ──

    async def _operator_call(method: str, params: dict[str, Any]) -> str:
        _ok, message, data = await asyncio.to_thread(core.operator_call, method, params)
        return _dump(R(_ok, message, data))

    @mcp.tool(name="sra_ocr", description="Perform OCR on the game window, returns all recognized texts")
    async def perform_ocr(
        fromX: int | None = None, fromY: int | None = None, toX: int | None = None, toY: int | None = None
    ) -> list[str]:
        result = await _operator_call(
            "ocr", {"from_x": fromX, "from_y": fromY, "to_x": toX, "to_y": toY}
        )
        return [result, _OCR_COORD_NOTE]

    @mcp.tool(
        name="sra_ocr_match", description="Perform OCR and match text on the game window, returns the matched text"
    )
    async def perform_ocr_match(
        text: str, fromX: int | None = None, fromY: int | None = None, toX: int | None = None, toY: int | None = None
    ) -> list[str]:
        result = await _operator_call(
            "ocr_match", {"text": text, "from_x": fromX, "from_y": fromY, "to_x": toX, "to_y": toY}
        )
        return [result, _OCR_COORD_NOTE]

    @mcp.tool(name="sra_click_point", description="Click on a point in the game window")
    async def click_point(mode: str, x: float, y: float) -> str:
        if mode not in ("abs", "rel"):
            return f'Invalid mode \'{mode}\', expected "abs" or "rel".'
        _ok, message, _data = await asyncio.to_thread(core.operator_call, "click_point", {"mode": mode, "x": x, "y": y})
        return message or _NO_RESPONSE_MSG

    @mcp.tool(name="sra_operator_list", description="List all available operator methods")
    async def list_operator_methods() -> str:
        return _dump(R(True, "Operator methods", core.operator_list()))

    @mcp.tool(name="sra_operator_help", description="Get detailed help (parameters, types and doc) for an operator method")
    async def operator_help(method: str) -> str:
        if not _valid_method_name(method):
            return f"Invalid method name '{method}'."
        data = core.operator_help(method)
        if data is None:
            return _dump(R(False, f"方法 '{method}' 不存在"))
        return _dump(R(True, method, data))

    @mcp.tool(
        name="sra_operator_call",
        description=(
            "Call any operator method with JSON parameters. Use sra_operator_list to discover methods "
            "and sra_operator_help for their parameters."
        ),
    )
    async def operator_call(method: str, parameters: str | None = None) -> str:
        if not _valid_method_name(method):
            return f"Invalid method name '{method}'."
        params: dict[str, Any] = {}
        if parameters and parameters.strip():
            try:
                parsed = json.loads(parameters)
            except json.JSONDecodeError as e:
                return f"Invalid parameters JSON: {e}"
            if not isinstance(parsed, dict):
                return 'parameters must be a JSON object, e.g. \'{"x":1}\''
            params = parsed
        return await _operator_call(method, params)

    @mcp.tool(name="sra_scroll", description="Scroll the mouse wheel")
    async def scroll(clicks: int, x: int | None = None, y: int | None = None) -> str:
        _ok, message, _data = await asyncio.to_thread(core.operator_call, "scroll", {"clicks": clicks, "x": x, "y": y})
        return message or _NO_RESPONSE_MSG

    @mcp.tool(name="sra_press_key", description="Press a key on the keyboard")
    async def press_key(key: str) -> str:
        _ok, message, _data = await asyncio.to_thread(core.operator_call, "press_key", {"key": key})
        return message or _NO_RESPONSE_MSG

    @mcp.tool(name="sra_hold_key", description="Hold a key on the keyboard")
    async def hold_key(key: str, duration: float = 1.0) -> str:
        _ok, message, _data = await asyncio.to_thread(
            core.operator_call, "hold_key", {"key": key, "duration": duration}
        )
        return message or _NO_RESPONSE_MSG

    @mcp.tool(name="sra_sleep", description="Pause the execution for a specified number of seconds")
    async def sleep(seconds: int) -> str:
        await asyncio.sleep(seconds)
        return f"Slept for {seconds} seconds"

    # ── 日志 ──

    @mcp.tool(name="sra_get_logs", description="Get the backend logs")
    async def get_logs(count: int = 100) -> str:
        return "\n".join(core.log_stream.recent(count))

    # ── 配置 ──

    @mcp.tool(name="sra_config_list", description="List all task config names and the current config name")
    async def list_configs() -> str:
        return _dump({"currentConfig": core.cache.current_config_name(), "configs": core.configs.names()})

    @mcp.tool(
        name="sra_config_get",
        description=(
            "Get a task config by name (username/password are masked). "
            "Field keys are dotted keys like currencyWars.runtimes"
        ),
    )
    async def get_config(configName: str) -> str:
        if not core.configs.exists(configName):
            return f"Config '{configName}' not found."
        return _dump(core.configs.masked_dict(configName))

    @mcp.tool(
        name="sra_config_create",
        description="Create a new task config (registers the name; the config file is written on first update)",
    )
    async def create_config(configName: str) -> str:
        if not core.configs.is_valid_name(configName):
            return "Config name contains invalid characters"
        if core.configs.exists(configName):
            return f"Config '{configName}' already exists"
        core.configs.create(configName)
        return f"Config '{configName}' created."

    @mcp.tool(
        name="sra_config_update",
        description=(
            "Patch a task config with a partial JSON object. Top-level keys are section names "
            "(startGame/trailblazePower/receiveRewards/cosmicStrife/missionAccomplished), inner keys are dotted "
            'field keys, e.g. {"cosmicStrife":{"currencyWars.runtimes":3,"currencyWars.pointRewards":true}}. '
            "Only provided fields are changed; startGame.username/password accept plaintext and are stored "
            "encrypted, unprovided fields are preserved."
        ),
    )
    async def update_config(configName: str, patchJson: str) -> str:
        if not core.configs.exists(configName):
            return f"Config '{configName}' not found."
        patch = _parse_patch(patchJson)
        if patch is None:
            return "Patch JSON must be an object"
        updated = await asyncio.to_thread(core.configs.patch, configName, patch)
        if not updated:
            return "No valid fields were updated"
        return f"Config '{configName}' updated: {', '.join(updated)}"

    @mcp.tool(
        name="sra_config_delete",
        description="Delete a task config registration (the config file on disk is kept)",
    )
    async def delete_config(configName: str) -> str:
        if not core.configs.delete(configName):
            return f"Config '{configName}' not found."
        return f"Config '{configName}' deleted."

    # ── 设置 ──

    @mcp.tool(
        name="sra_settings_get",
        description="Get the app settings. Field keys are dotted keys like developerMode.customBackend.enabled",
    )
    async def get_settings() -> str:
        return _dump(core.settings.get_dict())

    @mcp.tool(
        name="sra_settings_update",
        description=(
            "Patch app settings with a partial JSON object. Top-level keys are section names "
            '(general/display/update/advanced/notification), inner keys are dotted field keys, e.g. '
            '{"advanced":{"developerMode.customBackend.enabled":true}}. Only provided fields are changed.'
        ),
    )
    async def update_settings(patchJson: str) -> str:
        patch = _parse_patch(patchJson)
        if patch is None:
            return "Patch JSON must be an object"
        updated = await asyncio.to_thread(core.settings.patch, patch)
        if not updated:
            return "No valid settings were updated"
        return f"Settings updated: {', '.join(updated)}"

    return mcp


def _parse_patch(patch_json: str) -> dict[str, Any] | None:
    """解析 patch JSON 字符串，非对象返回 None。"""
    try:
        parsed = json.loads(patch_json)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")


def build_mcp_asgi(core, host: str) -> tuple[Any, Any]:
    """构造 MCP 的 ASGI 应用与会话管理器。

    Returns:
        (ASGI 应用, session_manager)；session_manager 需在 Litestar lifespan 中手动启动。
    """
    server = build_mcp_server(core)
    app = server.streamable_http_app(streamable_http_path="/mcp", stateless_http=True, host=host)
    return app, server.session_manager
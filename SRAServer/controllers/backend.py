"""Backend 控制器：重启/停止、最近日志、SSE 日志流与截图。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from litestar import Request, get, post
from litestar.params import FromQuery, JSONBody
from litestar.response import Response, ServerSentEvent, ServerSentEventMessage

from SRAServer.controllers._responses import core_of, json_response
from SRAServer.schemas.envelope import R
from SRAServer.schemas.requests import RestartRequest


@post("/api/backend/restart", status_code=200, summary="重启后端")
async def restart_backend(request: Request, data: JSONBody[RestartRequest | None] = None) -> Response:
    core = core_of(request)
    if core.config.visitor_mode:
        return json_response(R(True, "Backend restarted successfully"))
    try:
        await asyncio.to_thread(core.backend.restart)
        return json_response(R(True, "Backend restarted successfully"))
    except Exception:
        return json_response(R(False, "Failed to restart backend"), 500)


@post("/api/backend/stop", status_code=200, summary="停止后端")
async def stop_backend(request: Request) -> Response:
    """停止运行中的工作；若本进程持有 uvicorn Server，则一并触发优雅退出。

    进程内托管没有可终止的子进程，因此“停止后端”= 请求停止工作 + 让 uvicorn 退出
    （由 ``run_server`` 把 Server 实例挂到 ``app.state.uvicorn_server``）；
    测试/嵌入式场景没有该实例时只停工作，并在 message 里说明。
    """
    core = core_of(request)
    try:
        await asyncio.to_thread(core.backend.stop)
    except Exception:
        return json_response(R(False, "Failed to stop backend"), 500)

    server = getattr(request.app.state, "uvicorn_server", None)
    if server is not None:
        server.should_exit = True
        return json_response(R(True, "Backend stopped successfully"))
    return json_response(R(True, "Running tasks stopped; no in-process server to shut down"))


@get("/api/backend/logs", summary="获取最近日志")
async def get_recent_logs(request: Request, count: FromQuery[int] = 100) -> Response:
    return json_response(R(True, "success", core_of(request).log_stream.recent(count)))


@get("/api/backend/logs/stream", summary="SSE 日志流")
async def stream_logs(request: Request) -> Response:
    core = core_of(request)

    async def generate() -> AsyncIterator[ServerSentEventMessage]:
        yield ServerSentEventMessage(comment="Connected")
        async for line in core.log_stream.subscribe():
            yield ServerSentEventMessage(data=line)

    return ServerSentEvent(
        generate(),
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@get("/api/backend/screenshot", summary="获取 Operator 截图")
async def get_screenshot(request: Request) -> Response:
    core = core_of(request)
    if core.config.visitor_mode:
        return Response(content=b"", media_type="image/jpeg")
    message, data = await asyncio.to_thread(core.backend.screenshot)
    if not data:
        return json_response(R(False, f"Failed to get screenshot from backend: {message}"))
    return Response(content=data, media_type="image/jpeg")


HANDLERS = [restart_backend, stop_backend, get_recent_logs, stream_logs, get_screenshot]
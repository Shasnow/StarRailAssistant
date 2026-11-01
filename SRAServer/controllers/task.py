"""Task 控制器：运行任务/单个任务、停止与状态查询。"""

from __future__ import annotations

import asyncio
import json
import uuid

from litestar import Request, get, post
from litestar.params import JSONBody
from litestar.response import Response

from SRACore.util.const import ConfigsDir
from SRACore.util.logger import logger

from SRAServer.controllers._responses import core_of, json_response
from SRAServer.schemas.envelope import R
from SRAServer.schemas.requests import RunRequest, SingleTaskRequest


@post("/api/task/run", status_code=200, summary="运行任务")
async def run_task(request: Request, data: JSONBody[RunRequest]) -> Response:
    core = core_of(request)
    if core.config.visitor_mode:
        return json_response(R(True, "Task started"))

    if core.is_busy():
        return json_response(R(False, "A task is already running"), 409)

    config_name: str | None = None
    if data.config is not None:
        config_name = (data.config.get("name") if data.persist else None) or f"_api_{uuid.uuid4().hex}"
        ConfigsDir.mkdir(parents=True, exist_ok=True)
        # 临时配置用后即弃：此前若有任务运行会被上方的 is_busy 拦下，因此此刻可以安全清理遗留文件
        for stale in ConfigsDir.glob("_api_*.json"):
            try:
                stale.unlink()
            except OSError:
                logger.warning(f"Failed to remove stale temporary config: {stale}")
        path = ConfigsDir / f"{config_name}.json"
        path.write_text(json.dumps(data.config, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"{'Persisted' if data.persist else 'Created temporary'} config: {config_name}")
    elif data.config_name and data.config_name.strip():
        config_name = data.config_name.strip()
        if not (ConfigsDir / f"{config_name}.json").exists():
            return json_response(R(False, f"Config '{config_name}' not found"), 400)

    started = await asyncio.to_thread(core.run_configs, [config_name] if config_name else [])
    return json_response(
        R(True, "Task started") if started else R(False, "Failed to send task command to backend.")
    )


@post("/api/task/single", status_code=200, summary="运行单个指定任务")
async def run_single_task(request: Request, data: JSONBody[SingleTaskRequest]) -> Response:
    core = core_of(request)
    if core.config.visitor_mode:
        return json_response(R(True, "Single task started"))
    if core.is_busy():
        return json_response(R(False, "A task is already running"), 409)
    started = await asyncio.to_thread(core.run_single, data.task_name, data.config_name)
    return json_response(
        R(True, "Single task started") if started else R(False, "Failed to send single task command")
    )


@post("/api/task/stop", status_code=200, summary="停止任务")
async def stop_task(request: Request) -> Response:
    core = core_of(request)
    if not core.is_busy():
        return json_response(R(False, "No task is running"))
    await asyncio.to_thread(core.stop_running_work)
    return json_response(R(True, "Stop signal sent"))


@get("/api/task/status", summary="获取任务状态")
async def get_task_status(request: Request) -> Response:
    return json_response(R(True, "Task status", core_of(request).task_status()))


HANDLERS = [run_task, run_single_task, stop_task, get_task_status]
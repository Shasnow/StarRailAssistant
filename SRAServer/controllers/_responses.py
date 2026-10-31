"""控制器公共工具：JSON 响应构造与 SRACore 上下文获取。"""

from __future__ import annotations

import json
from typing import Any

from litestar import Request
from litestar.response import Response


def json_response(payload: Any, status_code: int = 200) -> Response:
    """构造 JSON 响应（统一走 json.dumps，避免序列化器对特殊类型的限制）。"""
    return Response(
        content=json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
        media_type="application/json",
        status_code=status_code,
    )


def core_of(request: Request):
    """获取当前请求对应的 ServerContext。"""
    return request.app.state.core
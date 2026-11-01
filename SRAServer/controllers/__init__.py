"""HTTP 控制器：与既有 C# 服务逐一对齐的 ``/api/**`` 路由集合。"""

from __future__ import annotations

from SRAServer.controllers import (
    app,
    auth,
    backend,
    configs,
    extensions,
    operator,
    settings,
    task,
)

# 所有路由处理器（顺序即注册顺序）
HANDLERS = [
    *app.HANDLERS,
    *auth.HANDLERS,
    *backend.HANDLERS,
    *configs.HANDLERS,
    *extensions.HANDLERS,
    *operator.HANDLERS,
    *settings.HANDLERS,
    *task.HANDLERS,
]

__all__ = ["HANDLERS"]
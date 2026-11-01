"""统一响应信封 R：{ success, message, data }（与服务端既有 R 记录一致）。"""

from __future__ import annotations

from typing import Any


def R(success: bool, message: str, data: Any = None) -> dict[str, Any]:
    """构造统一响应信封。

    Args:
        success: 业务是否成功。
        message: 提示信息。
        data: 附加数据，缺省为 None（序列化为 JSON null）。

    Returns:
        可直接被 Litestar 序列化的字典。
    """
    return {"success": success, "message": message, "data": data}
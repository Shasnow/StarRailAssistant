"""统一响应信封 R：{ success, message, data }（与服务端既有 R 记录一致）。

``message`` 固定为英文提示，**不做本地化**：它属于机器可读的协议文本，客户端不要
依赖其语言。需要本地化的展示文本请放在 ``data`` 中，由客户端按自身语言处理。
"""

from __future__ import annotations

from typing import Any


def R(success: bool, message: str, data: Any = None) -> dict[str, Any]:
    """构造统一响应信封。

    Args:
        success: 业务是否成功。
        message: 英文提示信息，不随界面语言变化。
        data: 附加数据，缺省为 None（序列化为 JSON null）。

    Returns:
        可直接被 Litestar 序列化的字典。
    """
    return {"success": success, "message": message, "data": data}
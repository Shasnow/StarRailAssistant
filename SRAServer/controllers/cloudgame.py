"""CloudGame 控制器：获取云游戏扫码登录使用的二维码。"""

from __future__ import annotations

from litestar import get
from litestar.response import Response

from SRACore.util.const import QrcodeLoginImage

from SRAServer.controllers._responses import json_response
from SRAServer.schemas.envelope import R


@get("/api/cloudgame/qrcode", summary="获取云游戏登录二维码")
async def get_cloudgame_qrcode() -> Response:
    """返回最近一次扫码登录保存的二维码图片（PNG，含静区）。

    二维码由启动游戏任务的扫码登录流程写入，尚未生成或已被清理时返回 404。
    """
    if not QrcodeLoginImage.is_file():
        return json_response(R(False, "QR code not available"), 404)
    return Response(
        content=QrcodeLoginImage.read_bytes(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


HANDLERS = [get_cloudgame_qrcode]

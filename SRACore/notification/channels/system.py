from __future__ import annotations

import io

import PIL.Image

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.models import NotificationContext
from SRACore.util.const import LogsScreenshotDir


class SystemChannel(NotificationChannel):
    name = "系统"
    enabled_attr = "isSystemEnabled"

    def send(self, context: NotificationContext) -> bool:
        try:
            from plyer import notification  # type: ignore
        except ImportError:
            print("plyer 模块未安装，无法发送系统通知")
            return True
        fn = getattr(notification, "notify", None)
        if callable(fn):
            fn(title=context.title, message=context.message, app_name="SRA", timeout=5)
        if context.screenshot_bytes is not None:
            # 保存截图到 AppRootDir/log/screenshot/ 目录
            filename = context.message.replace(" ", "_").replace("/", "_").replace("\\", "_").replace("。","")
            PIL.Image.open(io.BytesIO(context.screenshot_bytes)).save(LogsScreenshotDir / f"{filename}.png")
        return True


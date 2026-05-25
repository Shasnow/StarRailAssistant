from __future__ import annotations

from plyer import notification  # type: ignore

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.models import NotificationContext


class SystemChannel(NotificationChannel):
    name = "系统"
    enabled_attr = "isSystemEnabled"

    def send(self, context: NotificationContext) -> bool:
        fn = getattr(notification, "notify", None)
        if callable(fn):
            fn(title=context.title, message=context.message, app_name="SRA", timeout=5)
        return True


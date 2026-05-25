from __future__ import annotations

from typing import Any

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.http_client import HttpClient
from SRACore.notification.models import NotificationContext, format_notification_message


class XxtuiChannel(NotificationChannel):
    name = "xxtui"
    enabled_attr = "isXxtuiEnabled"

    def __init__(self, client: HttpClient):
        self.client = client

    def send(self, context: NotificationContext) -> bool:
        cfg = context.settings
        api_key = cfg.xxtuiApiKey.strip()
        if not api_key:
            return False
        payload: dict[str, Any] = {"title": "SRA 通知", "content": format_notification_message(context.payload)}
        if cfg.xxtuiSource.strip():
            payload["source"] = cfg.xxtuiSource.strip()
        if cfg.xxtuiChannel.strip():
            payload["channel"] = cfg.xxtuiChannel.strip()
        return self.client.post_json("https://xxtui.com/send/" + api_key, payload).ok


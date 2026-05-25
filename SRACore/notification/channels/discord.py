from __future__ import annotations

import json

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.http_client import HttpClient
from SRACore.notification.models import NotificationContext


class DiscordChannel(NotificationChannel):
    name = "Discord"
    enabled_attr = "isDiscordEnabled"

    def __init__(self, client: HttpClient):
        self.client = client

    def send(self, context: NotificationContext) -> bool:
        webhook_url = context.settings.discordWebhookUrl.strip()
        if not webhook_url:
            return False

        payload = {
            "username": "StarRailAssistant",
            "embeds": [{
                "title": "SRA 通知",
                "color": 0x00FF00 if context.payload.get("result") == "success" else 0xFF0000,
                "fields": [
                    {"name": "事件", "value": context.payload.get("event", ""), "inline": True},
                    {"name": "结果", "value": context.payload.get("result", ""), "inline": True},
                    {"name": "时间", "value": context.payload.get("timestamp", ""), "inline": True},
                    {"name": "消息", "value": context.payload.get("message", ""), "inline": False},
                ],
            }],
        }

        if context.settings.isDiscordSendImage:
            image = context.screenshot_bytes
            if image:
                boundary = "SRABoundary"
                crlf = b"\r\n"
                body = (
                    b"--" + boundary.encode() + crlf
                    + b'Content-Disposition: form-data; name="payload_json"' + crlf
                    + b"Content-Type: application/json" + crlf + crlf
                    + json.dumps(payload, ensure_ascii=False).encode() + crlf
                    + b"--" + boundary.encode() + crlf
                    + b'Content-Disposition: form-data; name="files[0]"; filename="screenshot.png"' + crlf
                    + b"Content-Type: image/png" + crlf + crlf
                    + image + crlf
                    + b"--" + boundary.encode() + b"--" + crlf
                )
                if self.client.post_multipart(webhook_url, body, boundary).ok:
                    return True

        return self.client.post_json(webhook_url, payload).ok


from __future__ import annotations

from typing import Any

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.http_client import HttpClient
from SRACore.notification.models import NotificationContext, format_notification_message


class BarkChannel(NotificationChannel):
    name = "Bark"
    enabled_attr = "isBarkEnabled"

    def __init__(self, client: HttpClient):
        self.client = client

    def send(self, context: NotificationContext) -> bool:
        cfg = context.settings
        keys = [k.strip() for k in cfg.barkDeviceKey.strip().split(",") if k.strip()]
        if not keys:
            return False
        server_url = cfg.barkServerUrl.strip().rstrip("/")
        payload: dict[str, Any] = {
            "title": "SRA 通知",
            "body": format_notification_message(context.payload),
            "group": cfg.barkGroup.strip() or "StarRailAssistant",
        }

        if cfg.barkLevel.strip() in ("active", "timeSensitive", "passive"):
            payload["level"] = cfg.barkLevel.strip()
        if cfg.barkSound.strip():
            payload["sound"] = cfg.barkSound.strip()
        if cfg.barkIcon.strip():
            payload["icon"] = cfg.barkIcon.strip()
        if cfg.barkCiphertext.strip():
            payload["ciphertext"] = cfg.barkCiphertext.strip()

        success = True
        for key in keys:
            if not self.client.post_json(server_url + "/" + key, payload).ok:
                success = False
        return success


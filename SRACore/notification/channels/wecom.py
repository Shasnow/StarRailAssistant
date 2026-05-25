from __future__ import annotations

import base64
import hashlib

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.channels.common import load_json_object
from SRACore.notification.http_client import HttpClient
from SRACore.notification.models import NotificationContext, format_notification_message
from SRACore.util.image_util import compress_image_bytes


def _wecom_ok(status: int, body: str) -> bool:
    if not (200 <= status < 300):
        return False
    parsed = load_json_object(body)
    return bool(parsed and parsed.get("errcode") == 0)


class WeComChannel(NotificationChannel):
    name = "企业微信"
    enabled_attr = "isWeComEnabled"

    def __init__(self, client: HttpClient):
        self.client = client

    def send(self, context: NotificationContext) -> bool:
        webhook_url = context.settings.weComWebhookUrl.strip()
        if not webhook_url:
            return False

        text_resp = self.client.post_json(
            webhook_url,
            {"msgtype": "text", "text": {"content": format_notification_message(context.payload)}},
        )
        if not _wecom_ok(text_resp.status_code, text_resp.body):
            return False

        if not context.settings.isWeComSendImage:
            return True

        image = context.screenshot_bytes
        if not image:
            return False

        target_size = 2 * 1024 * 1024
        image_to_send = image
        if len(image_to_send) > target_size:
            compressed, _, _ = compress_image_bytes(image_to_send, target_size)
            if not compressed:
                return False
            image_to_send = compressed

        image_payload = {
            "msgtype": "image",
            "image": {
                "base64": base64.b64encode(image_to_send).decode(),
                "md5": hashlib.md5(image_to_send).hexdigest(),
            },
        }
        resp = self.client.post_json(webhook_url, image_payload)
        return _wecom_ok(resp.status_code, resp.body)


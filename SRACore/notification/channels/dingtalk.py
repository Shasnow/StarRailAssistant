from __future__ import annotations

import base64
import hashlib
import hmac
import time
import urllib.parse

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.http_client import HttpClient
from SRACore.notification.models import NotificationContext


class DingTalkChannel(NotificationChannel):
    name = "钉钉"
    enabled_attr = "isDingTalkEnabled"

    def __init__(self, client: HttpClient):
        self.client = client

    def send(self, context: NotificationContext) -> bool:
        cfg = context.settings
        webhook_url = cfg.dingTalkWebhookUrl.strip()
        if not webhook_url:
            return False

        secret = cfg.dingTalkSecret.strip()
        if secret:
            timestamp = str(round(time.time() * 1000))
            sign_raw = timestamp + "\n" + secret
            hmac_code = hmac.new(secret.encode(), sign_raw.encode(), digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            webhook_url = webhook_url + "&timestamp=" + timestamp + "&sign=" + sign

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": "SRA 通知",
                "text": "\n".join([
                    "**[SRA 通知]**",
                    "",
                    "- 事件: " + str(context.payload.get("event", "")),
                    "- 结果: " + str(context.payload.get("result", "")),
                    "- 时间: " + str(context.payload.get("timestamp", "")),
                    "- 消息: " + str(context.payload.get("message", "")),
                ]),
            },
        }
        return self.client.post_json(webhook_url, payload).ok


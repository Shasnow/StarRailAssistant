from __future__ import annotations

import json

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.channels.common import load_json_object
from SRACore.notification.http_client import HttpClient
from SRACore.notification.models import NotificationContext, format_notification_message


class FeishuChannel(NotificationChannel):
    name = "飞书"
    enabled_attr = "isFeishuEnabled"

    def __init__(self, client: HttpClient):
        self.client = client

    def send(self, context: NotificationContext) -> bool:
        cfg = context.settings
        app_id = cfg.feishuAppId.strip()
        app_secret = cfg.feishuAppSecret.strip()
        msg = format_notification_message(context.payload)

        if app_id and app_secret:
            receive_id = cfg.feishuReceiveId.strip()
            id_type = cfg.feishuReceiveIdType.strip() or "open_id"
            if not receive_id:
                return False

            token_resp = self.client.post_json(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                {"app_id": app_id, "app_secret": app_secret},
            )
            token_json = load_json_object(token_resp.body)
            token = "" if token_json is None else str(token_json.get("tenant_access_token", ""))
            if not token:
                return False

            payload = {"receive_id": receive_id, "msg_type": "text", "content": json.dumps({"text": msg})}
            headers = {"Authorization": "Bearer " + token}
            return self.client.post_json(
                "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=" + id_type,
                payload,
                headers=headers,
            ).ok

        webhook_url = cfg.feishuWebhookUrl.strip()
        if not webhook_url:
            return False
        return self.client.post_json(webhook_url, {"msg_type": "text", "content": {"text": msg}}).ok


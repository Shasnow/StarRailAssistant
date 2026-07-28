from __future__ import annotations

import base64

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.http_client import HttpClient
from SRACore.notification.models import NotificationContext, format_notification_message
from SRACore.util.image_util import compress_image_bytes

# OneBot 图片大小限制（2MB，与企业微信一致）
_MAX_IMAGE_SIZE = 2 * 1024 * 1024


class OneBotChannel(NotificationChannel):
    name = "OneBot"
    enabled_attr = "isOneBotEnabled"

    def __init__(self, client: HttpClient):
        self.client = client

    def send(self, context: NotificationContext) -> bool:
        cfg = context.settings
        endpoint = cfg.oneBotUrl.strip().rstrip("/")
        user_id = cfg.oneBotUserId.strip()
        group_id = cfg.oneBotGroupId.strip()
        token = cfg.oneBotToken.strip()
        if not endpoint or (not user_id and not group_id):
            return False

        url = endpoint if endpoint.endswith("/send_msg") else endpoint + "/send_msg"
        headers = {"Authorization": "Bearer " + token} if token else None
        text_seg = [{"type": "text", "data": {"text": format_notification_message(context.payload)}}]

        ok = True
        if user_id:
            ok = self.client.post_json(url, {"message_type": "private", "user_id": user_id, "message": text_seg}, headers=headers).ok and ok
        if group_id:
            ok = self.client.post_json(url, {"message_type": "group", "group_id": group_id, "message": text_seg}, headers=headers).ok and ok

        if cfg.isOneBotSendImage:
            image = context.screenshot_bytes
            if image:
                image_data = image
                if len(image_data) > _MAX_IMAGE_SIZE:
                    compressed, _, _ = compress_image_bytes(image_data, _MAX_IMAGE_SIZE)
                    if compressed:
                        image_data = compressed
                image_seg = [{"type": "image", "data": {"file": "base64://" + base64.b64encode(image_data).decode()}}]
                if user_id:
                    self.client.post_json(url, {"message_type": "private", "user_id": user_id, "message": image_seg}, headers=headers)
                if group_id:
                    self.client.post_json(url, {"message_type": "group", "group_id": group_id, "message": image_seg}, headers=headers)
        return ok


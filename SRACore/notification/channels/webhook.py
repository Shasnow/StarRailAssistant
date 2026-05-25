from __future__ import annotations

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.http_client import HttpClient
from SRACore.notification.models import NotificationContext


class WebhookChannel(NotificationChannel):
    name = "Webhook"
    enabled_attr = "isWebhookEnabled"

    def __init__(self, client: HttpClient):
        self.client = client

    def send(self, context: NotificationContext) -> bool:
        endpoint = context.settings.webhookUrl.strip()
        if not endpoint:
            return False
        return self.client.post_json(endpoint, context.payload).ok


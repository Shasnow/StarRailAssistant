from __future__ import annotations

import re

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.http_client import HttpClient
from SRACore.notification.models import NotificationContext, format_notification_message


class ServerChanChannel(NotificationChannel):
    name = "ServerChan"
    enabled_attr = "isServerChanEnabled"

    def __init__(self, client: HttpClient):
        self.client = client

    def send(self, context: NotificationContext) -> bool:
        send_key = context.settings.serverChanSendKey.strip()
        if not send_key:
            return False
        if send_key.startswith("sctp"):
            matched = re.match(r"sctp(\d+)t", send_key)
            if not matched:
                return False
            url = "https://" + matched.group(1) + ".push.ft07.com/send/" + send_key + ".send"
        else:
            url = "https://sctapi.ftqq.com/" + send_key + ".send"
        payload = {"title": context.payload.get("title", "SRA 通知"), "desp": format_notification_message(context.payload)}
        return self.client.post_json(url, payload).ok


from __future__ import annotations

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.channels.common import build_multipart_body
from SRACore.notification.http_client import HttpClient
from SRACore.notification.models import NotificationContext, format_notification_message


class TelegramChannel(NotificationChannel):
    name = "Telegram"
    enabled_attr = "isTelegramEnabled"

    def __init__(self, client: HttpClient):
        self.client = client

    def send(self, context: NotificationContext) -> bool:
        cfg = context.settings
        bot_token = cfg.telegramBotToken.strip()
        chat_id = cfg.telegramChatId.strip()
        if not bot_token or not chat_id:
            return False

        api_base = cfg.telegramApiBaseUrl.strip()
        if not api_base:
            api_base = "https://api.telegram.org/bot"
        else:
            if not api_base.startswith(("http://", "https://")):
                api_base = "https://" + api_base
            if not api_base.endswith("/"):
                api_base += "/"
            if not api_base.endswith("/bot"):
                api_base += "bot"

        proxy_url = cfg.telegramProxyUrl.strip() if cfg.isTelegramProxyEnabled and cfg.telegramProxyUrl.strip() else None
        text_ok = self.client.post_json(
            api_base + bot_token + "/sendMessage",
            {"chat_id": chat_id, "text": format_notification_message(context.payload), "disable_web_page_preview": True},
            proxy_url=proxy_url,
        ).ok
        if not text_ok:
            return False

        if cfg.isTelegramSendImage:
            image = context.screenshot_bytes
            if image:
                boundary = "SRABoundary"
                body = build_multipart_body({"chat_id": chat_id}, "photo", "screenshot.png", "image/png", image, boundary)
                self.client.post_multipart(api_base + bot_token + "/sendPhoto", body, boundary, proxy_url=proxy_url)
        return True


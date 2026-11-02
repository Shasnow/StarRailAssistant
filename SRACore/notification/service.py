from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from SRACore.models.app_settings import NotificationSettings
from SRACore.notification.channels import (
    BarkChannel,
    DingTalkChannel,
    DiscordChannel,
    EmailChannel,
    FeishuChannel,
    OneBotChannel,
    ServerChanChannel,
    SystemChannel,
    TelegramChannel,
    WeComChannel,
    WebhookChannel,
    XxtuiChannel,
)
from SRACore.notification.dispatcher import NotificationDispatcher
from SRACore.notification.http_client import HttpClient
from SRACore.notification.models import NotificationContext, format_notification_message
from SRACore.util.logger import logger
from SRACore.localization import Resources

_cached_game_screenshot_bytes: bytes | None = None
_notification_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="notify_batch")
_notification_dispatcher = NotificationDispatcher(timeout=10, retries=1)
_http_client = HttpClient(timeout=10, retries=1)


_CHANNEL_LABELS: dict[str, str] = {
    "webhook": "Webhook",
    "telegram": "Telegram",
    "serverchan": "ServerChan",
    "onebot": "OneBot",
    "bark": "Bark",
    "discord": "Discord",
    "xxtui": "xxtui",
}

_CHANNEL_LABEL_KEYS: dict[str, str] = {
    "email": "notification.channelEmail",
    "feishu": "notification.channelFeishu",
    "wecom": "notification.channelWeCom",
    "dingtalk": "notification.channelDingTalk",
    "system": "notification.channelSystem",
}


def _channel_label(channel: str) -> str:
    """渠道显示名：品牌名保持原样，其余跟随界面语言。"""
    resource_key = _CHANNEL_LABEL_KEYS.get(channel)
    if resource_key:
        return Resources.get_translation(resource_key)
    return _CHANNEL_LABELS.get(channel, "")


def build_notification_payload(title: str, message: str, result: str = "success") -> dict[str, str]:
    return {
        "title": title,
        "message": message,
        "result": result,
        "event": title,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def should_capture_notification_screenshot(config: NotificationSettings) -> bool:
    return any([
        config.isTelegramEnabled and config.isTelegramSendImage,
        config.isOneBotEnabled and config.isOneBotSendImage,
        config.isWeComEnabled and config.isWeComSendImage,
        config.isDiscordEnabled and config.isDiscordSendImage,
        config.isSystemEnabled
    ])



def clear_cached_game_screenshot() -> None:
    global _cached_game_screenshot_bytes

    _cached_game_screenshot_bytes = None


def try_send_notification(settings: NotificationSettings,
                          title: str, message: str, result: str = "success", image: Any | None = None) -> None:
    if not settings.isEnabled:
        return

    screenshot_bytes = None
    if should_capture_notification_screenshot(settings):
        screenshot_bytes = _image_to_bytes(image)
        if not screenshot_bytes:
            screenshot_bytes = _get_cached_game_screenshot_bytes()

    context = NotificationContext(
        title=title,
        message=message,
        payload=build_notification_payload(title, message, result),
        settings=settings,
        screenshot_bytes=screenshot_bytes,
    )

    clear_cached_game_screenshot()
    _notification_executor.submit(_notification_dispatcher.dispatch, context)


def send_channel_test_notification(channel: str, settings: NotificationSettings) -> tuple[str, bool]:
    cfg = settings
    key = channel.strip().lower()
    label = _channel_label(key)
    if not label:
        return "", False

    payload = build_notification_payload(
        Resources.notification_testTitle,
        Resources.notification_testMessage,
        "success")
    test_image = _get_test_image_bytes() if _channel_needs_test_image(key, cfg) else None

    context = NotificationContext(
        title=str(payload["title"]),
        message=str(payload["message"]),
        payload=payload,
        settings=cfg,
        screenshot_bytes=test_image,
    )

    channel_obj = _build_channel(key)
    if channel_obj is None:
        return "", False
    try:
        return label, channel_obj.send(context)
    except Exception as err:
        logger.warning(label + " 测试通知发送失败：" + str(err))
        return label, False


def _build_channel(channel_key: str):
    match channel_key:
        case "email":
            return EmailChannel()
        case "webhook":
            return WebhookChannel(_http_client)
        case "telegram":
            return TelegramChannel(_http_client)
        case "serverchan":
            return ServerChanChannel(_http_client)
        case "onebot":
            return OneBotChannel(_http_client)
        case "bark":
            return BarkChannel(_http_client)
        case "feishu":
            return FeishuChannel(_http_client)
        case "wecom":
            return WeComChannel(_http_client)
        case "dingtalk":
            return DingTalkChannel(_http_client)
        case "discord":
            return DiscordChannel(_http_client)
        case "xxtui":
            return XxtuiChannel(_http_client)
        case "system":
            return SystemChannel()
    return None


def _channel_needs_test_image(channel_key: str, config: NotificationSettings) -> bool:
    if channel_key == "telegram":
        return config.isTelegramSendImage
    if channel_key == "onebot":
        return config.isOneBotSendImage
    if channel_key == "wecom":
        return config.isWeComSendImage
    if channel_key == "discord":
        return config.isDiscordSendImage
    return False


def _get_cached_game_screenshot_bytes() -> bytes | None:
    return _cached_game_screenshot_bytes


def _image_to_bytes(image: Any | None = None) -> bytes | None:
    try:
        import io

        if image is None:
            return None

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def _get_test_image_bytes() -> bytes | None:
    icon_path = Path("assets") / "SRAico.png"
    try:
        return icon_path.read_bytes()
    except Exception:
        return None


__all__ = [
    "build_notification_payload",
    "clear_cached_game_screenshot",
    "format_notification_message",
    "send_channel_test_notification",
    "should_capture_notification_screenshot",
    "try_send_notification",
]


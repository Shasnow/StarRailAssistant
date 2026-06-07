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
from SRACore.util.data_persister import load_app_settings
from SRACore.util.logger import logger


_cached_game_screenshot_bytes: bytes | None = None
_cached_game_screenshot_owner_id: int | None = None
_notification_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="notify_batch")
_notification_dispatcher = NotificationDispatcher(timeout=10, retries=1)
_http_client = HttpClient(timeout=10, retries=1)


_CHANNEL_LABELS: dict[str, str] = {
    "email": "邮件",
    "webhook": "Webhook",
    "telegram": "Telegram",
    "serverchan": "ServerChan",
    "onebot": "OneBot",
    "bark": "Bark",
    "feishu": "飞书",
    "wecom": "企业微信",
    "dingtalk": "钉钉",
    "discord": "Discord",
    "xxtui": "xxtui",
    "system": "System",
}


def load_notification_settings() -> NotificationSettings:
    settings = load_app_settings()
    return settings.Notification


def build_notification_payload(title: str, message: str, result: str = "success") -> dict[str, str]:
    return {
        "title": title,
        "message": message,
        "result": result,
        "event": title,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def should_capture_notification_screenshot(config: NotificationSettings | None = None) -> bool:
    cfg = config or load_notification_settings()
    return any([
        cfg.isTelegramEnabled and cfg.isTelegramSendImage,
        cfg.isOneBotEnabled and cfg.isOneBotSendImage,
        cfg.isWeComEnabled and cfg.isWeComSendImage,
        cfg.isDiscordEnabled and cfg.isDiscordSendImage,
        cfg.isSystemEnabled
    ])


def capture_game_screenshot(operator: Any | None = None) -> bytes | None:
    global _cached_game_screenshot_bytes, _cached_game_screenshot_owner_id

    image_bytes = _capture_game_window_bytes(operator)
    if image_bytes:
        _cached_game_screenshot_bytes = image_bytes
        _cached_game_screenshot_owner_id = id(operator) if operator is not None else None
    return image_bytes


def clear_cached_game_screenshot() -> None:
    global _cached_game_screenshot_bytes, _cached_game_screenshot_owner_id

    _cached_game_screenshot_bytes = None
    _cached_game_screenshot_owner_id = None


def try_send_notification(title: str, message: str, result: str = "success", operator: Any | None = None) -> None:
    settings = load_notification_settings()
    if not settings.isEnabled:
        return

    screenshot_bytes = None
    if should_capture_notification_screenshot(settings):
        screenshot_bytes = _capture_game_window_bytes(operator)
        if not screenshot_bytes:
            screenshot_bytes = _get_cached_game_screenshot_bytes(operator)

    context = NotificationContext(
        title=title,
        message=message,
        payload=build_notification_payload(title, message, result),
        settings=settings,
        screenshot_bytes=screenshot_bytes,
    )

    clear_cached_game_screenshot()
    _notification_executor.submit(_notification_dispatcher.dispatch, context)


def send_channel_test_notification(channel: str, settings: NotificationSettings | None = None) -> tuple[str, bool]:
    cfg = settings or load_notification_settings()
    key = channel.strip().lower()
    label = _CHANNEL_LABELS.get(key, "")
    if not label:
        return "", False

    payload = build_notification_payload(
        "通知渠道测试",
        "这是一条测试通知, 如果你收到此通知，证明你的渠道配置正确",
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


def _get_cached_game_screenshot_bytes(operator: Any | None = None) -> bytes | None:
    if _cached_game_screenshot_bytes is None:
        return None
    if operator is None:
        return _cached_game_screenshot_bytes
    if _cached_game_screenshot_owner_id == id(operator):
        return _cached_game_screenshot_bytes
    return None


def _capture_game_window_bytes(operator: Any | None = None) -> bytes | None:
    try:
        import io

        if operator is None:
            return None

        screenshot = operator.screenshot()
        buf = io.BytesIO()
        screenshot.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def _take_screenshot_bytes() -> bytes | None:
    cached = _get_cached_game_screenshot_bytes()
    if cached:
        return cached
    return capture_game_screenshot()


def _get_test_image_bytes() -> bytes | None:
    icon_path = Path("resources") / "SRAico.png"
    try:
        return icon_path.read_bytes()
    except Exception:
        return None


__all__ = [
    "build_notification_payload",
    "capture_game_screenshot",
    "clear_cached_game_screenshot",
    "format_notification_message",
    "load_notification_settings",
    "send_channel_test_notification",
    "should_capture_notification_screenshot",
    "try_send_notification",
]


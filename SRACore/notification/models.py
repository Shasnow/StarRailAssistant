from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from SRACore.models.app_settings import NotificationSettings
from SRACore.localization.presentation import translate


@dataclass(frozen=True)
class NotificationContext:
    """Immutable notification context shared by all channels."""

    title: str
    message: str
    payload: dict[str, Any]
    settings: NotificationSettings
    screenshot_bytes: bytes | None = None


def format_notification_message(payload: dict[str, Any]) -> str:
    lines = [
        translate("[SRA 通知]"),
        translate("事件: ") + translate(str(payload.get("event", ""))),
        translate("结果: ") + str(payload.get("result", "")),
        translate("时间: ") + str(payload.get("timestamp", "")),
        translate("消息: ") + translate(str(payload.get("message", ""))),
    ]
    return "\n".join(lines)


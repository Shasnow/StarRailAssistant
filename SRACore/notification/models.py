from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from SRACore.models.app_settings import NotificationSettings


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
        "[SRA 通知]",
        "事件: " + str(payload.get("event", "")),
        "结果: " + str(payload.get("result", "")),
        "时间: " + str(payload.get("timestamp", "")),
        "消息: " + str(payload.get("message", "")),
    ]
    return "\n".join(lines)


from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from SRACore.models.app_settings import NotificationSettings
from SRACore.localization import Resources


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
        Resources.notification_payloadHeader,
        Resources.notification_payloadEvent + str(payload.get("event", "")),
        Resources.notification_payloadResult + str(payload.get("result", "")),
        Resources.notification_payloadTime + str(payload.get("timestamp", "")),
        Resources.notification_payloadMessage + str(payload.get("message", "")),
    ]
    return "\n".join(lines)

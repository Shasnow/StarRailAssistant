from __future__ import annotations

from abc import ABC, abstractmethod

from SRACore.notification.models import NotificationContext


class NotificationChannel(ABC):
    name: str = ""
    enabled_attr: str = ""

    @abstractmethod
    def send(self, context: NotificationContext) -> bool:
        raise NotImplementedError


from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from SRACore.notification.channels import build_channels
from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.http_client import HttpClient
from SRACore.notification.models import NotificationContext


class NotificationDispatcher:
    """Dispatch notifications to enabled channels with isolated error handling."""

    def __init__(self, timeout: int = 10, retries: int = 1):
        self._client = HttpClient(timeout=timeout, retries=retries)
        self._channels: list[NotificationChannel] = build_channels(self._client)

    def dispatch(self, context: NotificationContext) -> None:
        channels = [ch for ch in self._channels if getattr(context.settings, ch.enabled_attr, False)]
        if not channels:
            return

        with ThreadPoolExecutor(max_workers=len(channels), thread_name_prefix="notify") as executor:
            futures = [executor.submit(self._run_channel, channel, context) for channel in channels]
            for future in futures:
                future.result()

    @staticmethod
    def _run_channel(channel: NotificationChannel, context: NotificationContext) -> None:
        from SRACore.util.logger import logger

        try:
            ok = channel.send(context)
            if ok:
                logger.debug(channel.name + " 通知发送成功")
            else:
                logger.warning(channel.name + " 通知发送失败")
        except Exception as err:
            logger.warning(channel.name + " 通知发送失败: " + str(err))


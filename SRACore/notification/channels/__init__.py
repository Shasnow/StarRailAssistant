from __future__ import annotations

from SRACore.notification.channels.bark import BarkChannel
from SRACore.notification.channels.dingtalk import DingTalkChannel
from SRACore.notification.channels.discord import DiscordChannel
from SRACore.notification.channels.email import EmailChannel
from SRACore.notification.channels.feishu import FeishuChannel
from SRACore.notification.channels.onebot import OneBotChannel
from SRACore.notification.channels.serverchan import ServerChanChannel
from SRACore.notification.channels.system import SystemChannel
from SRACore.notification.channels.telegram import TelegramChannel
from SRACore.notification.channels.wecom import WeComChannel
from SRACore.notification.channels.webhook import WebhookChannel
from SRACore.notification.channels.xxtui import XxtuiChannel
from SRACore.notification.http_client import HttpClient


def build_channels(client: HttpClient):
    return [
        SystemChannel(),
        EmailChannel(),
        WebhookChannel(client),
        TelegramChannel(client),
        ServerChanChannel(client),
        OneBotChannel(client),
        BarkChannel(client),
        FeishuChannel(client),
        WeComChannel(client),
        DingTalkChannel(client),
        DiscordChannel(client),
        XxtuiChannel(client),
    ]


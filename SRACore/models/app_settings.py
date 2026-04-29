#!/usr/bin/env python3
"""
自动生成的Python类
源文件: AppSettings.cs
"""

from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class AppSettings:
    """自动生成的 AppSettings 类"""

    General: GeneralSettings = None
    Display: DisplaySettings = None
    Update: UpdateSettings = None
    Advanced: AdvancedSettings = None
    Notification: NotificationSettings = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "general": self.General.to_dict(),
            "display": self.Display.to_dict(),
            "update": self.Update.to_dict(),
            "advanced": self.Advanced.to_dict(),
            "notification": self.Notification.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "General": GeneralSettings.from_dict(data.get("general", {})),
            "Display": DisplaySettings.from_dict(data.get("display", {})),
            "Update": UpdateSettings.from_dict(data.get("update", {})),
            "Advanced": AdvancedSettings.from_dict(data.get("advanced", {})),
            "Notification": NotificationSettings.from_dict(data.get("notification", {}))
        })

@dataclass
class GeneralSettings:
    """自动生成的 GeneralSettings 类"""

    gamePaths: list[str] = field(default_factory=list)
    gamePathIndex: int = 0
    isAutoDetectGamePath: bool = True
    isCloudGameEnable: bool = False
    templateMatchConfidence: float = 0.9
    isOverlayEnabled: bool = False
    isGameArgsEnabled: bool = False
    gameArgsWindowSize: str = "1920x1080"
    gameArgsFullScreenMode: str = "窗口化"
    isGameArgsPopupWindow: bool = False
    gameArgsAdvanced: str = ""
    isUseCmd: bool = False
    hotkeyStop: str = "F9"
    hotkeyF1: str = "F1"
    hotkeyF2: str = "F2"
    hotkeyF3: str = "F3"
    hotkeyF4: str = "F4"
    hotkeyM: str = "M"
    hotkeyE: str = "E"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "gamePath.uris": self.gamePaths,
            "gamePath.index": self.gamePathIndex,
            "gamePath.autoDetect": self.isAutoDetectGamePath,
            "cloudGame.enabled": self.isCloudGameEnable,
            "templateMatchConfidence": self.templateMatchConfidence,
            "overlay.enabled": self.isOverlayEnabled,
            "gameArgs.enabled": self.isGameArgsEnabled,
            "gameArgs.windowSize": self.gameArgsWindowSize,
            "gameArgs.fullScreenMode": self.gameArgsFullScreenMode,
            "gameArgs.popupWindow": self.isGameArgsPopupWindow,
            "gameArgs.advanced": self.gameArgsAdvanced,
            "gameArgs.useCmd": self.isUseCmd,
            "keybindings.stop": self.hotkeyStop,
            "keybindings.f1": self.hotkeyF1,
            "keybindings.f2": self.hotkeyF2,
            "keybindings.f3": self.hotkeyF3,
            "keybindings.f4": self.hotkeyF4,
            "keybindings.m": self.hotkeyM,
            "keybindings.e": self.hotkeyE
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "gamePaths": data.get("gamePath.uris", list()),
            "gamePathIndex": data.get("gamePath.index", 0),
            "isAutoDetectGamePath": data.get("gamePath.autoDetect", True),
            "isCloudGameEnable": data.get("cloudGame.enabled", False),
            "templateMatchConfidence": data.get("templateMatchConfidence", 0.9),
            "isOverlayEnabled": data.get("overlay.enabled", False),
            "isGameArgsEnabled": data.get("gameArgs.enabled", False),
            "gameArgsWindowSize": data.get("gameArgs.windowSize", "1920x1080"),
            "gameArgsFullScreenMode": data.get("gameArgs.fullScreenMode", "窗口化"),
            "isGameArgsPopupWindow": data.get("gameArgs.popupWindow", False),
            "gameArgsAdvanced": data.get("gameArgs.advanced", ""),
            "isUseCmd": data.get("gameArgs.useCmd", False),
            "hotkeyStop": data.get("keybindings.stop", "F9"),
            "hotkeyF1": data.get("keybindings.f1", "F1"),
            "hotkeyF2": data.get("keybindings.f2", "F2"),
            "hotkeyF3": data.get("keybindings.f3", "F3"),
            "hotkeyF4": data.get("keybindings.f4", "F4"),
            "hotkeyM": data.get("keybindings.m", "M"),
            "hotkeyE": data.get("keybindings.e", "E")
        })

@dataclass
class DisplaySettings:
    """自动生成的 DisplaySettings 类"""

    backgroundImageUri: str = ""
    backgroundOpacity: float = 1
    controlPanelOpacity: float = 0.9
    language: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "backgroundImage.uri": self.backgroundImageUri,
            "backgroundImage.opacity": self.backgroundOpacity,
            "controlPanel.opacity": self.controlPanelOpacity,
            "language": self.language
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "backgroundImageUri": data.get("backgroundImage.uri", ""),
            "backgroundOpacity": data.get("backgroundImage.opacity", 1),
            "controlPanelOpacity": data.get("controlPanel.opacity", 0.9),
            "language": data.get("language", 0)
        })

@dataclass
class NotificationSettings:
    """自动生成的 NotificationSettings 类"""

    isEnabled: bool = False
    isSystemEnabled: bool = False
    isEmailEnabled: bool = False
    smtpServer: str = ""
    smtpPort: int = 465
    smtpSender: str = ""
    EncryptedSmtpAuthCode: str = ""
    smtpReceiver: str = ""
    isWebhookEnabled: bool = False
    webhookUrl: str = ""
    isTelegramEnabled: bool = False
    telegramBotToken: str = ""
    telegramChatId: str = ""
    isTelegramProxyEnabled: bool = False
    telegramProxyUrl: str = "http://127.0.0.1:7890"
    telegramApiBaseUrl: str = "https://api.telegram.org"
    isTelegramSendImage: bool = False
    isServerChanEnabled: bool = False
    serverChanSendKey: str = ""
    isOneBotEnabled: bool = False
    oneBotUrl: str = ""
    oneBotUserId: str = ""
    oneBotGroupId: str = ""
    oneBotToken: str = ""
    isOneBotSendImage: bool = False
    isBarkEnabled: bool = False
    barkServerUrl: str = "https://api.day.app"
    barkDeviceKey: str = ""
    barkGroup: str = "StarRailAssistant"
    barkLevel: str = ""
    barkSound: str = ""
    barkIcon: str = ""
    barkCiphertext: str = ""
    isFeishuEnabled: bool = False
    feishuWebhookUrl: str = ""
    feishuAppId: str = ""
    feishuAppSecret: str = ""
    feishuReceiveId: str = ""
    feishuReceiveIdType: str = ""
    isWeComEnabled: bool = False
    weComWebhookUrl: str = ""
    isWeComSendImage: bool = False
    isDingTalkEnabled: bool = False
    dingTalkWebhookUrl: str = ""
    dingTalkSecret: str = ""
    isDiscordEnabled: bool = False
    discordWebhookUrl: str = ""
    isDiscordSendImage: bool = False
    isXxtuiEnabled: bool = False
    xxtuiApiKey: str = ""
    xxtuiSource: str = ""
    xxtuiChannel: str = ""
    onStart: list[str] = field(default_factory=list)
    onComplete: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "enabled": self.isEnabled,
            "system.enabled": self.isSystemEnabled,
            "email.enabled": self.isEmailEnabled,
            "email.smtpServer": self.smtpServer,
            "email.smtpPort": self.smtpPort,
            "email.smtpSender": self.smtpSender,
            "email.smtpAuthCode": self.EncryptedSmtpAuthCode,
            "email.smtpReceiver": self.smtpReceiver,
            "webhook.enabled": self.isWebhookEnabled,
            "webhook.url": self.webhookUrl,
            "telegram.enabled": self.isTelegramEnabled,
            "telegram.botToken": self.telegramBotToken,
            "telegram.chatId": self.telegramChatId,
            "telegram.proxyEnabled": self.isTelegramProxyEnabled,
            "telegram.proxyUrl": self.telegramProxyUrl,
            "telegram.apiBaseUrl": self.telegramApiBaseUrl,
            "telegram.sendImage": self.isTelegramSendImage,
            "serverChan.enabled": self.isServerChanEnabled,
            "serverChan.sendKey": self.serverChanSendKey,
            "oneBot.enabled": self.isOneBotEnabled,
            "oneBot.url": self.oneBotUrl,
            "oneBot.userId": self.oneBotUserId,
            "oneBot.groupId": self.oneBotGroupId,
            "oneBot.token": self.oneBotToken,
            "oneBot.sendImage": self.isOneBotSendImage,
            "bark.enabled": self.isBarkEnabled,
            "bark.serverUrl": self.barkServerUrl,
            "bark.deviceKey": self.barkDeviceKey,
            "bark.group": self.barkGroup,
            "bark.level": self.barkLevel,
            "bark.sound": self.barkSound,
            "bark.icon": self.barkIcon,
            "bark.ciphertext": self.barkCiphertext,
            "feishu.enabled": self.isFeishuEnabled,
            "feishu.webhookUrl": self.feishuWebhookUrl,
            "feishu.appId": self.feishuAppId,
            "feishu.appSecret": self.feishuAppSecret,
            "feishu.receiveId": self.feishuReceiveId,
            "feishu.receiveIdType": self.feishuReceiveIdType,
            "weCom.enabled": self.isWeComEnabled,
            "weCom.webhookUrl": self.weComWebhookUrl,
            "weCom.sendImage": self.isWeComSendImage,
            "dingTalk.enabled": self.isDingTalkEnabled,
            "dingTalk.webhookUrl": self.dingTalkWebhookUrl,
            "dingTalk.secret": self.dingTalkSecret,
            "discord.enabled": self.isDiscordEnabled,
            "discord.webhookUrl": self.discordWebhookUrl,
            "discord.sendImage": self.isDiscordSendImage,
            "xxtui.enabled": self.isXxtuiEnabled,
            "xxtui.apiKey": self.xxtuiApiKey,
            "xxtui.source": self.xxtuiSource,
            "xxtui.channel": self.xxtuiChannel,
            "onStart": self.onStart,
            "onComplete": self.onComplete
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "isEnabled": data.get("enabled", False),
            "isSystemEnabled": data.get("system.enabled", False),
            "isEmailEnabled": data.get("email.enabled", False),
            "smtpServer": data.get("email.smtpServer", ""),
            "smtpPort": data.get("email.smtpPort", 465),
            "smtpSender": data.get("email.smtpSender", ""),
            "EncryptedSmtpAuthCode": data.get("email.smtpAuthCode", ""),
            "smtpReceiver": data.get("email.smtpReceiver", ""),
            "isWebhookEnabled": data.get("webhook.enabled", False),
            "webhookUrl": data.get("webhook.url", ""),
            "isTelegramEnabled": data.get("telegram.enabled", False),
            "telegramBotToken": data.get("telegram.botToken", ""),
            "telegramChatId": data.get("telegram.chatId", ""),
            "isTelegramProxyEnabled": data.get("telegram.proxyEnabled", False),
            "telegramProxyUrl": data.get("telegram.proxyUrl", "http://127.0.0.1:7890"),
            "telegramApiBaseUrl": data.get("telegram.apiBaseUrl", "https://api.telegram.org"),
            "isTelegramSendImage": data.get("telegram.sendImage", False),
            "isServerChanEnabled": data.get("serverChan.enabled", False),
            "serverChanSendKey": data.get("serverChan.sendKey", ""),
            "isOneBotEnabled": data.get("oneBot.enabled", False),
            "oneBotUrl": data.get("oneBot.url", ""),
            "oneBotUserId": data.get("oneBot.userId", ""),
            "oneBotGroupId": data.get("oneBot.groupId", ""),
            "oneBotToken": data.get("oneBot.token", ""),
            "isOneBotSendImage": data.get("oneBot.sendImage", False),
            "isBarkEnabled": data.get("bark.enabled", False),
            "barkServerUrl": data.get("bark.serverUrl", "https://api.day.app"),
            "barkDeviceKey": data.get("bark.deviceKey", ""),
            "barkGroup": data.get("bark.group", "StarRailAssistant"),
            "barkLevel": data.get("bark.level", ""),
            "barkSound": data.get("bark.sound", ""),
            "barkIcon": data.get("bark.icon", ""),
            "barkCiphertext": data.get("bark.ciphertext", ""),
            "isFeishuEnabled": data.get("feishu.enabled", False),
            "feishuWebhookUrl": data.get("feishu.webhookUrl", ""),
            "feishuAppId": data.get("feishu.appId", ""),
            "feishuAppSecret": data.get("feishu.appSecret", ""),
            "feishuReceiveId": data.get("feishu.receiveId", ""),
            "feishuReceiveIdType": data.get("feishu.receiveIdType", ""),
            "isWeComEnabled": data.get("weCom.enabled", False),
            "weComWebhookUrl": data.get("weCom.webhookUrl", ""),
            "isWeComSendImage": data.get("weCom.sendImage", False),
            "isDingTalkEnabled": data.get("dingTalk.enabled", False),
            "dingTalkWebhookUrl": data.get("dingTalk.webhookUrl", ""),
            "dingTalkSecret": data.get("dingTalk.secret", ""),
            "isDiscordEnabled": data.get("discord.enabled", False),
            "discordWebhookUrl": data.get("discord.webhookUrl", ""),
            "isDiscordSendImage": data.get("discord.sendImage", False),
            "isXxtuiEnabled": data.get("xxtui.enabled", False),
            "xxtuiApiKey": data.get("xxtui.apiKey", ""),
            "xxtuiSource": data.get("xxtui.source", ""),
            "xxtuiChannel": data.get("xxtui.channel", ""),
            "onStart": data.get("onStart", list()),
            "onComplete": data.get("onComplete", list())
        })

@dataclass
class UpdateSettings:
    """自动生成的 UpdateSettings 类"""

    isCheckForUpdates: bool = True
    isAutoUpdate: bool = False
    EncryptedMirrorChyanCdk: str = ""
    downloadChannel: int = 0
    updateChannel: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "checkForUpdates": self.isCheckForUpdates,
            "autoUpdate": self.isAutoUpdate,
            "mirrorChyanCdk": self.EncryptedMirrorChyanCdk,
            "downloadChannel": self.downloadChannel,
            "updateChannel": self.updateChannel
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "isCheckForUpdates": data.get("checkForUpdates", True),
            "isAutoUpdate": data.get("autoUpdate", False),
            "EncryptedMirrorChyanCdk": data.get("mirrorChyanCdk", ""),
            "downloadChannel": data.get("downloadChannel", 0),
            "updateChannel": data.get("updateChannel", 0)
        })

@dataclass
class AdvancedSettings:
    """自动生成的 AdvancedSettings 类"""

    backendLaunchArgs: str = ""
    isDeveloperModeEnabled: bool = False
    isSaveOcrImage: bool = False
    isDebugOverlayEnabled: bool = False
    isUsePython: bool = False
    pythonPath: str = ""
    pythonMain: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "backendLaunchArgs": self.backendLaunchArgs,
            "developerMode.enabled": self.isDeveloperModeEnabled,
            "developerMode.saveOcrImage": self.isSaveOcrImage,
            "developerMode.overlay": self.isDebugOverlayEnabled,
            "developerMode.usePython": self.isUsePython,
            "developerMode.pythonPath": self.pythonPath,
            "developerMode.pythonMain": self.pythonMain
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "backendLaunchArgs": data.get("backendLaunchArgs", ""),
            "isDeveloperModeEnabled": data.get("developerMode.enabled", False),
            "isSaveOcrImage": data.get("developerMode.saveOcrImage", False),
            "isDebugOverlayEnabled": data.get("developerMode.overlay", False),
            "isUsePython": data.get("developerMode.usePython", False),
            "pythonPath": data.get("developerMode.pythonPath", ""),
            "pythonMain": data.get("developerMode.pythonMain", "")
        })

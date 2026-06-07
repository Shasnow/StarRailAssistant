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

    gamePathIndex: int = 0
    gamePaths: list[str] = field(default_factory=list)
    isAutoDetectGamePath: bool = True
    isGameArgsEnabled: bool = False
    gameArgsFullScreenMode: str = "窗口化"
    gameArgsWindowSize: str = "1920x1080"
    isGameArgsPopupWindow: bool = False
    isUseCmd: bool = False
    gameArgsAdvanced: str = ""
    isCloudGameEnable: bool = False
    cloudGameBrowser: str = "Microsoft Edge"
    hotkeyE: str = "E"
    hotkeyF1: str = "F1"
    hotkeyF2: str = "F2"
    hotkeyF3: str = "F3"
    hotkeyF4: str = "F4"
    hotkeyStop: str = "F9"
    isOverlayEnabled: bool = False
    ocrMatchConfidence: float = 0.7
    templateMatchConfidence: float = 0.9

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "gamePath.index": self.gamePathIndex,
            "gamePath.uris": self.gamePaths,
            "gamePath.autoDetect": self.isAutoDetectGamePath,
            "gameArgs.enabled": self.isGameArgsEnabled,
            "gameArgs.fullScreenMode": self.gameArgsFullScreenMode,
            "gameArgs.windowSize": self.gameArgsWindowSize,
            "gameArgs.popupWindow": self.isGameArgsPopupWindow,
            "gameArgs.useCmd": self.isUseCmd,
            "gameArgs.advanced": self.gameArgsAdvanced,
            "cloudGame.enabled": self.isCloudGameEnable,
            "cloudGame.browser": self.cloudGameBrowser,
            "keybindings.e": self.hotkeyE,
            "keybindings.f1": self.hotkeyF1,
            "keybindings.f2": self.hotkeyF2,
            "keybindings.f3": self.hotkeyF3,
            "keybindings.f4": self.hotkeyF4,
            "keybindings.stop": self.hotkeyStop,
            "overlay.enabled": self.isOverlayEnabled,
            "ocrMatchConfidence": self.ocrMatchConfidence,
            "templateMatchConfidence": self.templateMatchConfidence
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "gamePathIndex": data.get("gamePath.index", 0),
            "gamePaths": data.get("gamePath.uris", list()),
            "isAutoDetectGamePath": data.get("gamePath.autoDetect", True),
            "isGameArgsEnabled": data.get("gameArgs.enabled", False),
            "gameArgsFullScreenMode": data.get("gameArgs.fullScreenMode", "窗口化"),
            "gameArgsWindowSize": data.get("gameArgs.windowSize", "1920x1080"),
            "isGameArgsPopupWindow": data.get("gameArgs.popupWindow", False),
            "isUseCmd": data.get("gameArgs.useCmd", False),
            "gameArgsAdvanced": data.get("gameArgs.advanced", ""),
            "isCloudGameEnable": data.get("cloudGame.enabled", False),
            "cloudGameBrowser": data.get("cloudGame.browser", "Microsoft Edge"),
            "hotkeyE": data.get("keybindings.e", "E"),
            "hotkeyF1": data.get("keybindings.f1", "F1"),
            "hotkeyF2": data.get("keybindings.f2", "F2"),
            "hotkeyF3": data.get("keybindings.f3", "F3"),
            "hotkeyF4": data.get("keybindings.f4", "F4"),
            "hotkeyStop": data.get("keybindings.stop", "F9"),
            "isOverlayEnabled": data.get("overlay.enabled", False),
            "ocrMatchConfidence": data.get("ocrMatchConfidence", 0.7),
            "templateMatchConfidence": data.get("templateMatchConfidence", 0.9)
        })

@dataclass
class DisplaySettings:
    """自动生成的 DisplaySettings 类"""

    backgroundImageUri: str = ""
    backgroundOpacity: float = 1
    controlPanelOpacity: float = 0.9
    language: int = 0
    isRememberWindow: bool = False
    WindowState: int = 0
    WindowPositionX: int = 0
    WindowPositionY: int = 0
    WindowWidth: float = 0.0
    WindowHeight: float = 0.0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "backgroundImage.uri": self.backgroundImageUri,
            "backgroundImage.opacity": self.backgroundOpacity,
            "controlPanel.opacity": self.controlPanelOpacity,
            "language": self.language,
            "window.remember": self.isRememberWindow,
            "window.state": self.WindowState,
            "window.position.x": self.WindowPositionX,
            "window.position.y": self.WindowPositionY,
            "window.width": self.WindowWidth,
            "window.height": self.WindowHeight
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "backgroundImageUri": data.get("backgroundImage.uri", ""),
            "backgroundOpacity": data.get("backgroundImage.opacity", 1),
            "controlPanelOpacity": data.get("controlPanel.opacity", 0.9),
            "language": data.get("language", 0),
            "isRememberWindow": data.get("window.remember", False),
            "WindowState": data.get("window.state", 0),
            "WindowPositionX": data.get("window.position.x", 0),
            "WindowPositionY": data.get("window.position.y", 0),
            "WindowWidth": data.get("window.width", 0.0),
            "WindowHeight": data.get("window.height", 0.0)
        })

@dataclass
class NotificationSettings:
    """自动生成的 NotificationSettings 类"""

    isEnabled: bool = False
    isSystemEnabled: bool = False
    isBarkEnabled: bool = False
    barkCiphertext: str = ""
    barkDeviceKey: str = ""
    barkGroup: str = "StarRailAssistant"
    barkIcon: str = ""
    barkLevel: str = ""
    barkServerUrl: str = "https://api.day.app"
    barkSound: str = ""
    isDingTalkEnabled: bool = False
    dingTalkSecret: str = ""
    dingTalkWebhookUrl: str = ""
    isDiscordEnabled: bool = False
    isDiscordSendImage: bool = False
    discordWebhookUrl: str = ""
    isFeishuEnabled: bool = False
    feishuAppId: str = ""
    feishuAppSecret: str = ""
    feishuReceiveId: str = ""
    feishuReceiveIdType: str = ""
    feishuWebhookUrl: str = ""
    isOneBotEnabled: bool = False
    isOneBotSendImage: bool = False
    oneBotGroupId: str = ""
    oneBotToken: str = ""
    oneBotUrl: str = ""
    oneBotUserId: str = ""
    isServerChanEnabled: bool = False
    serverChanSendKey: str = ""
    isTelegramEnabled: bool = False
    isTelegramProxyEnabled: bool = False
    isTelegramSendImage: bool = False
    isWeComEnabled: bool = False
    isWeComSendImage: bool = False
    weComWebhookUrl: str = ""
    isWebhookEnabled: bool = False
    webhookUrl: str = ""
    isXxtuiEnabled: bool = False
    isEmailEnabled: bool = False
    smtpPort: int = 465
    smtpReceiver: str = ""
    smtpSender: str = ""
    smtpServer: str = ""
    EncryptedSmtpAuthCode: str = ""
    telegramApiBaseUrl: str = "https://api.telegram.org"
    telegramBotToken: str = ""
    telegramChatId: str = ""
    telegramProxyUrl: str = "http://127.0.0.1:7890"
    xxtuiApiKey: str = ""
    xxtuiChannel: str = ""
    xxtuiSource: str = ""
    onCompleted: list[str] = field(default_factory=list)
    onStart: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "enabled": self.isEnabled,
            "system.enabled": self.isSystemEnabled,
            "bark.enabled": self.isBarkEnabled,
            "bark.ciphertext": self.barkCiphertext,
            "bark.deviceKey": self.barkDeviceKey,
            "bark.group": self.barkGroup,
            "bark.icon": self.barkIcon,
            "bark.level": self.barkLevel,
            "bark.serverUrl": self.barkServerUrl,
            "bark.sound": self.barkSound,
            "dingTalk.enabled": self.isDingTalkEnabled,
            "dingTalk.secret": self.dingTalkSecret,
            "dingTalk.webhookUrl": self.dingTalkWebhookUrl,
            "discord.enabled": self.isDiscordEnabled,
            "discord.sendImage": self.isDiscordSendImage,
            "discord.webhookUrl": self.discordWebhookUrl,
            "feishu.enabled": self.isFeishuEnabled,
            "feishu.appId": self.feishuAppId,
            "feishu.appSecret": self.feishuAppSecret,
            "feishu.receiveId": self.feishuReceiveId,
            "feishu.receiveIdType": self.feishuReceiveIdType,
            "feishu.webhookUrl": self.feishuWebhookUrl,
            "oneBot.enabled": self.isOneBotEnabled,
            "oneBot.sendImage": self.isOneBotSendImage,
            "oneBot.groupId": self.oneBotGroupId,
            "oneBot.token": self.oneBotToken,
            "oneBot.url": self.oneBotUrl,
            "oneBot.userId": self.oneBotUserId,
            "serverChan.enabled": self.isServerChanEnabled,
            "serverChan.sendKey": self.serverChanSendKey,
            "telegram.enabled": self.isTelegramEnabled,
            "telegram.proxyEnabled": self.isTelegramProxyEnabled,
            "telegram.sendImage": self.isTelegramSendImage,
            "weCom.enabled": self.isWeComEnabled,
            "weCom.sendImage": self.isWeComSendImage,
            "weCom.webhookUrl": self.weComWebhookUrl,
            "webhook.enabled": self.isWebhookEnabled,
            "webhook.url": self.webhookUrl,
            "xxtui.enabled": self.isXxtuiEnabled,
            "email.enabled": self.isEmailEnabled,
            "email.smtpPort": self.smtpPort,
            "email.smtpReceiver": self.smtpReceiver,
            "email.smtpSender": self.smtpSender,
            "email.smtpServer": self.smtpServer,
            "email.smtpAuthCode": self.EncryptedSmtpAuthCode,
            "telegram.apiBaseUrl": self.telegramApiBaseUrl,
            "telegram.botToken": self.telegramBotToken,
            "telegram.chatId": self.telegramChatId,
            "telegram.proxyUrl": self.telegramProxyUrl,
            "xxtui.apiKey": self.xxtuiApiKey,
            "xxtui.channel": self.xxtuiChannel,
            "xxtui.source": self.xxtuiSource,
            "onCompleted": self.onCompleted,
            "onStart": self.onStart
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "isEnabled": data.get("enabled", False),
            "isSystemEnabled": data.get("system.enabled", False),
            "isBarkEnabled": data.get("bark.enabled", False),
            "barkCiphertext": data.get("bark.ciphertext", ""),
            "barkDeviceKey": data.get("bark.deviceKey", ""),
            "barkGroup": data.get("bark.group", "StarRailAssistant"),
            "barkIcon": data.get("bark.icon", ""),
            "barkLevel": data.get("bark.level", ""),
            "barkServerUrl": data.get("bark.serverUrl", "https://api.day.app"),
            "barkSound": data.get("bark.sound", ""),
            "isDingTalkEnabled": data.get("dingTalk.enabled", False),
            "dingTalkSecret": data.get("dingTalk.secret", ""),
            "dingTalkWebhookUrl": data.get("dingTalk.webhookUrl", ""),
            "isDiscordEnabled": data.get("discord.enabled", False),
            "isDiscordSendImage": data.get("discord.sendImage", False),
            "discordWebhookUrl": data.get("discord.webhookUrl", ""),
            "isFeishuEnabled": data.get("feishu.enabled", False),
            "feishuAppId": data.get("feishu.appId", ""),
            "feishuAppSecret": data.get("feishu.appSecret", ""),
            "feishuReceiveId": data.get("feishu.receiveId", ""),
            "feishuReceiveIdType": data.get("feishu.receiveIdType", ""),
            "feishuWebhookUrl": data.get("feishu.webhookUrl", ""),
            "isOneBotEnabled": data.get("oneBot.enabled", False),
            "isOneBotSendImage": data.get("oneBot.sendImage", False),
            "oneBotGroupId": data.get("oneBot.groupId", ""),
            "oneBotToken": data.get("oneBot.token", ""),
            "oneBotUrl": data.get("oneBot.url", ""),
            "oneBotUserId": data.get("oneBot.userId", ""),
            "isServerChanEnabled": data.get("serverChan.enabled", False),
            "serverChanSendKey": data.get("serverChan.sendKey", ""),
            "isTelegramEnabled": data.get("telegram.enabled", False),
            "isTelegramProxyEnabled": data.get("telegram.proxyEnabled", False),
            "isTelegramSendImage": data.get("telegram.sendImage", False),
            "isWeComEnabled": data.get("weCom.enabled", False),
            "isWeComSendImage": data.get("weCom.sendImage", False),
            "weComWebhookUrl": data.get("weCom.webhookUrl", ""),
            "isWebhookEnabled": data.get("webhook.enabled", False),
            "webhookUrl": data.get("webhook.url", ""),
            "isXxtuiEnabled": data.get("xxtui.enabled", False),
            "isEmailEnabled": data.get("email.enabled", False),
            "smtpPort": data.get("email.smtpPort", 465),
            "smtpReceiver": data.get("email.smtpReceiver", ""),
            "smtpSender": data.get("email.smtpSender", ""),
            "smtpServer": data.get("email.smtpServer", ""),
            "EncryptedSmtpAuthCode": data.get("email.smtpAuthCode", ""),
            "telegramApiBaseUrl": data.get("telegram.apiBaseUrl", "https://api.telegram.org"),
            "telegramBotToken": data.get("telegram.botToken", ""),
            "telegramChatId": data.get("telegram.chatId", ""),
            "telegramProxyUrl": data.get("telegram.proxyUrl", "http://127.0.0.1:7890"),
            "xxtuiApiKey": data.get("xxtui.apiKey", ""),
            "xxtuiChannel": data.get("xxtui.channel", ""),
            "xxtuiSource": data.get("xxtui.source", ""),
            "onCompleted": data.get("onCompleted", list()),
            "onStart": data.get("onStart", list())
        })

@dataclass
class UpdateSettings:
    """自动生成的 UpdateSettings 类"""

    downloadChannel: int = 0
    isAutoUpdate: bool = False
    isCheckForUpdates: bool = True
    updateChannel: int = 0
    EncryptedMirrorChyanCdk: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "downloadChannel": self.downloadChannel,
            "autoUpdate": self.isAutoUpdate,
            "checkForUpdates": self.isCheckForUpdates,
            "updateChannel": self.updateChannel,
            "mirrorChyanCdk": self.EncryptedMirrorChyanCdk
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "downloadChannel": data.get("downloadChannel", 0),
            "isAutoUpdate": data.get("autoUpdate", False),
            "isCheckForUpdates": data.get("checkForUpdates", True),
            "updateChannel": data.get("updateChannel", 0),
            "EncryptedMirrorChyanCdk": data.get("mirrorChyanCdk", "")
        })

@dataclass
class AdvancedSettings:
    """自动生成的 AdvancedSettings 类"""

    backendLaunchArgs: str = "--inline"
    isRemoteEnabled: bool = False
    remoteBaseUrl: str = "http://localhost:5000"
    isDebugOverlayEnabled: bool = False
    isDeveloperModeEnabled: bool = False
    isPythonEnabled: bool = False
    isSaveOcrImage: bool = False
    pythonMain: str = ""
    pythonPath: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "backend.launchArgs": self.backendLaunchArgs,
            "backend.remote.enabled": self.isRemoteEnabled,
            "backend.remote.baseUrl": self.remoteBaseUrl,
            "developerMode.overlay": self.isDebugOverlayEnabled,
            "developerMode.enabled": self.isDeveloperModeEnabled,
            "developerMode.python.enabled": self.isPythonEnabled,
            "developerMode.saveOcrImage": self.isSaveOcrImage,
            "developerMode.python.main": self.pythonMain,
            "developerMode.python.path": self.pythonPath
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "backendLaunchArgs": data.get("backend.launchArgs", "--inline"),
            "isRemoteEnabled": data.get("backend.remote.enabled", False),
            "remoteBaseUrl": data.get("backend.remote.baseUrl", "http://localhost:5000"),
            "isDebugOverlayEnabled": data.get("developerMode.overlay", False),
            "isDeveloperModeEnabled": data.get("developerMode.enabled", False),
            "isPythonEnabled": data.get("developerMode.python.enabled", False),
            "isSaveOcrImage": data.get("developerMode.saveOcrImage", False),
            "pythonMain": data.get("developerMode.python.main", ""),
            "pythonPath": data.get("developerMode.python.path", "")
        })

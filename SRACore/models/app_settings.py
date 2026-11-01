#!/usr/bin/env python3
"""
自动生成的 Pydantic 模型
源文件: SRAFrontend/SRAFrontend/Models/AppSettings.cs

SRACore 运行时与 SRAServer 的 OpenAPI 组件共用这一套模型定义，请勿手工编辑：
改动请修改对应的 C# 模型并执行 `npm run modelgen`。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    """生成模型基类：允许按字段名或 JSON 别名构造，并保留未知键。"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

class GeneralSettings(_Model):
    """通用设置。"""

    gamePathIndex: int = Field(0, alias="gamePath.index", description='游戏路径索引，指向 gamePath.uris 中的一个 URI')
    gamePaths: list[str] = Field(default_factory=list, alias="gamePath.uris", description='游戏路径列表，支持多个路径以便快速切换')
    isAutoDetectGamePath: bool = Field(True, alias="gamePath.autoDetect", description='是否自动检测游戏路径，启用后将扫描常见安装位置以找到游戏路径')
    isGameArgsEnabled: bool = Field(False, alias="gameArgs.enabled", description='是否启用游戏启动参数，启用后将使用下面的参数启动游戏')
    gameArgsFullScreenMode: str = Field("窗口化", alias="gameArgs.fullScreenMode", description='游戏窗口模式，如 窗口化、全屏')
    gameArgsWindowSize: str = Field("1920x1080", alias="gameArgs.windowSize", description='游戏窗口尺寸，格式为 宽x高，如 1920x1080')
    isGameArgsPopupWindow: bool = Field(False, alias="gameArgs.popupWindow", description='是否使用无边框游戏窗口')
    isGameArgsAutoButtle: bool = Field(True, alias="gameArgs.autoButtle", description='是否启用自动战斗')
    isUseCmd: bool = Field(False, alias="gameArgs.useCmd", description='是否使用命令行启动游戏（避免一些直接启动导致的问题）')
    gameArgsAdvanced: str = Field("", alias="gameArgs.advanced", description='高级启动参数，直接传递给游戏进程，覆盖其他参数设置')
    isCloudGameEnabled: bool = Field(False, alias="cloudGame.enabled", description='是否使用云游戏')
    cloudGameBrowser: str = Field("Microsoft Edge", alias="cloudGame.browser", description='云游戏使用的浏览器')
    cloudGameBrowserPath: str = Field("", alias="cloudGame.browser.path", description='云游戏使用的浏览器路径')
    isCloudGameBrowserHeadless: bool = Field(False, alias="cloudGame.browser.headless", description='云游戏使用的浏览器是否无头模式')
    isCloudGameBrowserMuteAudio: bool = Field(False, alias="cloudGame.browser.muteAudio", description='云游戏使用的浏览器是否静音')
    hotkeyE: str = Field("E", alias="keybindings.e", description='施放秘技的快捷键')
    hotkeyF1: str = Field("F1", alias="keybindings.f1", description='打开活动界面的快捷键')
    hotkeyF2: str = Field("F2", alias="keybindings.f2", description='打开纪行界面的快捷键')
    hotkeyF3: str = Field("F3", alias="keybindings.f3", description='打开卡池界面的快捷键')
    hotkeyF4: str = Field("F4", alias="keybindings.f4", description='打开指南界面的快捷键')
    hotkeyStop: str = Field("F9", alias="keybindings.stop", description='停止运行任务的快捷键')
    isOverlayEnabled: bool = Field(False, alias="overlay.enabled", description='是否启用叠加层')
    ocrMatchConfidence: float = Field(0.7, alias="ocrMatchConfidence", description='OCR 识图置信度，范围 0-1，数值越高越严格')
    templateMatchConfidence: float = Field(0.9, alias="templateMatchConfidence", description='模板匹配置信度（识图置信度），范围 0-1，数值越高越严格')
    isRetryOnTaskFailure: bool = Field(False, alias="isRetryOnTaskFailure", description='任务失败后是否尝试重启游戏并重试')
    maxRetryCount: int = Field(3, alias="maxRetryCount", description='任务失败后最大重试次数')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "GeneralSettings":
        """从字典创建对象"""
        return cls.model_validate(data)

class DisplaySettings(_Model):
    """显示设置。"""

    backgroundImageUri: str = Field("", alias="backgroundImage.uri", description='背景图片 URI，可以是本地路径或网络 URL')
    backgroundOpacity: float = Field(1.0, alias="backgroundImage.opacity", description='背景图片不透明度，范围 0-1')
    controlPanelOpacity: float = Field(0.9, alias="controlPanel.opacity", description='控制面板不透明度，范围 0-1')
    Language: int = Field(0, alias="language", description='界面语言，0=中文, 1=English')
    isRememberWindow: bool = Field(False, alias="window.remember", description='是否记住窗口位置和大小')
    WindowState: int = Field(0, alias="window.state", description='窗口状态，0=正常, 1=最小化, 2=最大化')
    WindowPositionX: int = Field(0, alias="window.position.x", description='主窗口位置的 X 坐标')
    WindowPositionY: int = Field(0, alias="window.position.y", description='主窗口位置的 Y 坐标')
    WindowWidth: float = Field(0.0, alias="window.width", description='主窗口宽度')
    WindowHeight: float = Field(0.0, alias="window.height", description='主窗口高度')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "DisplaySettings":
        """从字典创建对象"""
        return cls.model_validate(data)

class NotificationSettings(_Model):
    """通知设置。"""

    isEnabled: bool = Field(False, alias="enabled", description='是否启用通知功能')
    isSystemEnabled: bool = Field(False, alias="system.enabled", description='是否启用系统通知')
    isBarkEnabled: bool = Field(False, alias="bark.enabled", description='是否启用 Bark 推送')
    barkCiphertext: str = Field("", alias="bark.ciphertext", description='Bark 推送的密文内容，设置后作为 ciphertext 参数发送')
    barkDeviceKey: str = Field("", alias="bark.deviceKey", description='Bark 设备 Key，支持逗号分隔多个设备')
    barkGroup: str = Field("StarRailAssistant", alias="bark.group", description='Bark 消息分组')
    barkIcon: str = Field("", alias="bark.icon", description='Bark 推送图标的 URL')
    barkLevel: str = Field("", alias="bark.level", description='Bark 推送级别，active/timeSensitive/passive')
    barkServerUrl: str = Field("https://api.day.app", alias="bark.serverUrl", description='Bark 服务器地址')
    barkSound: str = Field("", alias="bark.sound", description='Bark 推送提示音名称')
    isDingTalkEnabled: bool = Field(False, alias="dingTalk.enabled", description='是否启用钉钉机器人推送')
    dingTalkSecret: str = Field("", alias="dingTalk.secret", description='钉钉机器人的加签密钥（SEC 开头）')
    dingTalkWebhookUrl: str = Field("", alias="dingTalk.webhookUrl", description='钉钉机器人的 Webhook 地址')
    isDiscordEnabled: bool = Field(False, alias="discord.enabled", description='是否启用 Discord 推送')
    isDiscordSendImage: bool = Field(False, alias="discord.sendImage", description='是否在 Discord 推送中附带截图')
    discordWebhookUrl: str = Field("", alias="discord.webhookUrl", description='Discord 的 Webhook 地址')
    isFeishuEnabled: bool = Field(False, alias="feishu.enabled", description='是否启用飞书推送')
    feishuAppId: str = Field("", alias="feishu.appId", description='飞书应用的 App ID')
    feishuAppSecret: str = Field("", alias="feishu.appSecret", description='飞书应用的 App Secret')
    feishuReceiveId: str = Field("", alias="feishu.receiveId", description='飞书消息接收者 ID')
    feishuReceiveIdType: str = Field("", alias="feishu.receiveIdType", description='飞书接收者 ID 类型，如 open_id、user_id、union_id、chat_id')
    feishuWebhookUrl: str = Field("", alias="feishu.webhookUrl", description='飞书机器人的 Webhook 地址')
    isOneBotEnabled: bool = Field(False, alias="oneBot.enabled", description='是否启用 OneBot 推送')
    isOneBotSendImage: bool = Field(False, alias="oneBot.sendImage", description='是否在 OneBot 推送中附带截图')
    oneBotGroupId: str = Field("", alias="oneBot.groupId", description='OneBot 推送的目标群号')
    oneBotToken: str = Field("", alias="oneBot.token", description='OneBot 的访问 Token')
    oneBotUrl: str = Field("", alias="oneBot.url", description='OneBot 的 HTTP API 地址')
    oneBotUserId: str = Field("", alias="oneBot.userId", description='OneBot 机器人的账号')
    isServerChanEnabled: bool = Field(False, alias="serverChan.enabled", description='是否启用 Server酱 推送')
    serverChanSendKey: str = Field("", alias="serverChan.sendKey", description='Server酱 的 SendKey')
    isTelegramEnabled: bool = Field(False, alias="telegram.enabled", description='是否启用 Telegram 推送')
    isTelegramProxyEnabled: bool = Field(False, alias="telegram.proxyEnabled", description='是否为 Telegram 推送启用代理')
    isTelegramSendImage: bool = Field(False, alias="telegram.sendImage", description='是否在 Telegram 推送中附带截图')
    isWeComEnabled: bool = Field(False, alias="weCom.enabled", description='是否启用企业微信推送')
    isWeComSendImage: bool = Field(False, alias="weCom.sendImage", description='是否在企业微信推送中附带截图')
    weComWebhookUrl: str = Field("", alias="weCom.webhookUrl", description='企业微信机器人的 Webhook 地址')
    isWebhookEnabled: bool = Field(False, alias="webhook.enabled", description='是否启用自定义 Webhook 推送')
    webhookUrl: str = Field("", alias="webhook.url", description='自定义 Webhook 的 URL')
    isXxtuiEnabled: bool = Field(False, alias="xxtui.enabled", description='是否启用 息知(xxtui) 推送')
    isEmailEnabled: bool = Field(False, alias="email.enabled", description='是否启用邮件推送')
    smtpPort: int = Field(465, alias="email.smtpPort", description='SMTP 服务器端口，SSL 通常为 465')
    smtpReceiver: str = Field("", alias="email.smtpReceiver", description='收件邮箱地址')
    smtpSender: str = Field("", alias="email.smtpSender", description='发件邮箱地址')
    smtpServer: str = Field("", alias="email.smtpServer", description='SMTP 服务器地址')
    EncryptedSmtpAuthCode: str = Field("", alias="email.smtpAuthCode", description='SMTP 授权码（加密存储）')
    telegramApiBaseUrl: str = Field("https://api.telegram.org", alias="telegram.apiBaseUrl", description='Telegram Bot API 地址')
    telegramBotToken: str = Field("", alias="telegram.botToken", description='Telegram 机器人的 Bot Token')
    telegramChatId: str = Field("", alias="telegram.chatId", description='Telegram 推送目标 Chat ID')
    telegramProxyUrl: str = Field("http://127.0.0.1:7890", alias="telegram.proxyUrl", description='Telegram 代理服务器地址')
    xxtuiApiKey: str = Field("", alias="xxtui.apiKey", description='息知(xxtui) 的 API Key')
    xxtuiChannel: str = Field("", alias="xxtui.channel", description='息知(xxtui) 的推送通道')
    xxtuiSource: str = Field("", alias="xxtui.source", description='息知(xxtui) 的消息来源')
    onCompleted: list[str] = Field(default_factory=list, alias="onCompleted", description='任务完成时发送通知的任务名称列表')
    onStart: list[str] = Field(default_factory=list, alias="onStart", description='任务开始时发送通知的任务名称列表')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "NotificationSettings":
        """从字典创建对象"""
        return cls.model_validate(data)

class UpdateSettings(_Model):
    """更新设置。"""

    downloadChannel: int = Field(0, alias="downloadChannel", description='下载渠道，0=Mirror Chyan, 1=Github Release, 2=AUTO-MAS')
    isAutoUpdate: bool = Field(False, alias="autoUpdate", description='是否启用自动更新: 将在有更新时直接开始下载')
    isCheckForUpdates: bool = Field(True, alias="checkForUpdates", description='是否启用检查更新功能: 将在启动时检查更新并提示用户')
    updateChannel: int = Field(0, alias="updateChannel", description='更新频道，0=Stable, 1=Beta')
    downloadPath: str = Field("", alias="downloadPath", description='更新安装包的下载保存目录，留空则使用系统临时目录下的 SRA 文件夹')
    EncryptedMirrorChyanCdk: str = Field("", alias="mirrorChyanCdk", description='Mirror Chyan 下载渠道的授权码，敏感信息将被加密存储')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "UpdateSettings":
        """从字典创建对象"""
        return cls.model_validate(data)

class AdvancedSettings(_Model):
    """高级设置。"""

    backendLaunchArgs: str = Field("--inline", alias="backend.launchArgs", description='后端启动参数')
    isRemoteEnabled: bool = Field(False, alias="backend.remote.enabled", description='是否使用远程后端')
    remoteBaseUrl: str = Field("http://localhost:5073", alias="backend.remote.baseUrl", description='远程后端地址')
    isDebugOverlayEnabled: bool = Field(False, alias="developerMode.overlay", description='是否在叠加层显示调试信息')
    isDeveloperModeEnabled: bool = Field(False, alias="developerMode.enabled", description='是否启用开发者模式')
    isCustomBackendEnabled: bool = Field(False, alias="developerMode.customBackend.enabled", description='是否启用自定义后端')
    customBackendCommand: str = Field("", alias="developerMode.customBackend.command", description='自定义后端命令/可执行文件，如 python、sra-cli、uv 或可执行文件路径')
    customBackendArguments: str = Field("", alias="developerMode.customBackend.arguments", description='自定义后端启动参数，如 main.py、-m SRACore')
    customBackendWorkingDirectory: str = Field("", alias="developerMode.customBackend.workingDirectory", description='自定义后端工作目录，留空时使用程序当前目录')
    isSaveOcrImage: bool = Field(False, alias="developerMode.saveOcrImage", description='是否保存 OCR 截图以便调试')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "AdvancedSettings":
        """从字典创建对象"""
        return cls.model_validate(data)

class AppSettings(_Model):
    """自动生成的 AppSettings 类"""

    General: GeneralSettings = Field(default_factory=GeneralSettings, alias="general", description='通用设置')
    Display: DisplaySettings = Field(default_factory=DisplaySettings, alias="display", description='显示设置')
    Update: UpdateSettings = Field(default_factory=UpdateSettings, alias="update", description='更新设置')
    Advanced: AdvancedSettings = Field(default_factory=AdvancedSettings, alias="advanced", description='高级设置')
    Notification: NotificationSettings = Field(default_factory=NotificationSettings, alias="notification", description='通知设置')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        """从字典创建对象"""
        return cls.model_validate(data)

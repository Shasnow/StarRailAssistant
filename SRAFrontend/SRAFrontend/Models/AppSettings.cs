using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Text.Json.Serialization;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

public class AppSettings
{
    public const string Version = "2.23.0-beta.1"; // 应用版本号

    [JsonPropertyName("general"), Description("通用设置")] public GeneralSettings General { get; init; } = new();

    [JsonPropertyName("display"), Description("显示设置")] public DisplaySettings Display { get; init; } = new();

    [JsonPropertyName("update"), Description("更新设置")] public UpdateSettings Update { get; init; } = new();

    [JsonPropertyName("advanced"), Description("高级设置")] public AdvancedSettings Advanced { get; init; } = new();

    [JsonPropertyName("notification"), Description("通知设置")] public NotificationSettings Notification { get; init; } = new();
}

public partial class GeneralSettings : ObservableObject
{
    [ObservableProperty]
    [property: JsonPropertyName("gamePath.index")]
    [property: Description("游戏路径索引，指向 gamePath.uris 中的一个 URI")]
    private int _gamePathIndex;

    [ObservableProperty]
    [property: JsonPropertyName("gamePath.uris")]
    [property: Description("游戏路径列表，支持多个路径以便快速切换")]
    private ObservableCollection<string> _gamePaths = [];

    [ObservableProperty]
    [property: JsonPropertyName("gamePath.autoDetect")]
    [property: Description("是否自动检测游戏路径，启用后将扫描常见安装位置以找到游戏路径")]
    private bool _isAutoDetectGamePath = true;

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.enabled")]
    [property: Description("是否启用游戏启动参数，启用后将使用下面的参数启动游戏")]
    private bool _isGameArgsEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.fullScreenMode")]
    [property: Description("游戏窗口模式，如 窗口化、全屏")]
    private string _gameArgsFullScreenMode = "窗口化";

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.windowSize")]
    [property: Description("游戏窗口尺寸，格式为 宽x高，如 1920x1080")]
    private string _gameArgsWindowSize = "1920x1080";

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.popupWindow")]
    [property: Description("是否使用无边框游戏窗口")]
    private bool _isGameArgsPopupWindow;

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.useCmd")]
    [property: Description("是否使用命令行启动游戏（避免一些直接启动导致的问题）")]
    private bool _isUseCmd;

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.advanced")]
    [property: Description("高级启动参数，直接传递给游戏进程，覆盖其他参数设置")]
    private string _gameArgsAdvanced = "";

    [ObservableProperty]
    [property: JsonPropertyName("cloudGame.enabled")]
    [property: Description("是否使用云游戏")]
    private bool _isCloudGameEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("cloudGame.browser")]
    [property: Description("云游戏使用的浏览器")]
    private string _cloudGameBrowser = "Microsoft Edge";

    [ObservableProperty]
    [property: JsonPropertyName("cloudGame.browser.path")]
    [property: Description("云游戏使用的浏览器路径")]
    private string _cloudGameBrowserPath = "";

    [ObservableProperty]
    [property: JsonPropertyName("cloudGame.browser.headless")]
    [property: Description("云游戏使用的浏览器是否无头模式")]
    private bool _isCloudGameBrowserHeadless;

    [ObservableProperty]
    [property: JsonPropertyName("cloudGame.browser.muteAudio")]
    [property: Description("云游戏使用的浏览器是否静音")]
    private bool _isCloudGameBrowserMuteAudio;

    [ObservableProperty]
    [property: JsonPropertyName("keybindings.e")]
    [property: Description("施放秘技的快捷键")]
    private string _hotkeyE = "E";

    [ObservableProperty]
    [property: JsonPropertyName("keybindings.f1")]
    [property: Description("打开活动界面的快捷键")]
    private string _hotkeyF1 = "F1";

    [ObservableProperty]
    [property: JsonPropertyName("keybindings.f2")]
    [property: Description("打开纪行界面的快捷键")]
    private string _hotkeyF2 = "F2";

    [ObservableProperty]
    [property: JsonPropertyName("keybindings.f3")]
    [property: Description("打开卡池界面的快捷键")]
    private string _hotkeyF3 = "F3";

    [ObservableProperty]
    [property: JsonPropertyName("keybindings.f4")]
    [property: Description("打开指南界面的快捷键")]
    private string _hotkeyF4 = "F4";

    [ObservableProperty]
    [property: JsonPropertyName("keybindings.stop")]
    [property: Description("停止运行任务的快捷键")]
    private string _hotkeyStop = "F9";

    [ObservableProperty]
    [property: JsonPropertyName("overlay.enabled")]
    [property: Description("是否启用叠加层")]
    private bool _isOverlayEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("ocrMatchConfidence")]
    [property: Description("OCR 识图置信度，范围 0-1，数值越高越严格")]
    [property: DefaultValue(0.7)]
    private double _ocrMatchConfidence = 0.7;

    [ObservableProperty]
    [property: JsonPropertyName("templateMatchConfidence")]
    [property: Description("模板匹配置信度（识图置信度），范围 0-1，数值越高越严格")]
    [property: DefaultValue(0.9)]
    private double _templateMatchConfidence = 0.9;

    [ObservableProperty]
    [property: JsonPropertyName("isRetryOnTaskFailure")]
    [property: Description("任务失败后是否尝试重启游戏并重试")]
    private bool _isRetryOnTaskFailure;

    [ObservableProperty]
    [property: JsonPropertyName("maxRetryCount")]
    [property: Description("任务失败后最大重试次数")]
    [property: DefaultValue(3)]
    private int _maxRetryCount = 3;
}

public partial class DisplaySettings : ObservableObject
{
    [ObservableProperty]
    [property: JsonPropertyName("backgroundImage.uri")]
    [property: Description("背景图片 URI，可以是本地路径或网络 URL")]
    private string _backgroundImageUri = "";

    [ObservableProperty]
    [property: JsonPropertyName("backgroundImage.opacity")]
    [property: Description("背景图片不透明度，范围 0-1")]
    private double _backgroundOpacity = 1;

    [ObservableProperty]
    [property: JsonPropertyName("controlPanel.opacity")]
    [property: Description("控制面板不透明度，范围 0-1")]
    private double _controlPanelOpacity = 0.9;

    [ObservableProperty]
    [JsonPropertyName("language")]
    [Description("界面语言，0=中文, 1=English")]
    public partial int Language { get; set; }

    [ObservableProperty]
    [property: JsonPropertyName("window.remember")]
    [property: Description("是否记住窗口位置和大小")]
    private bool _isRememberWindow;

    [JsonPropertyName("window.state")]
    [Description("窗口状态，0=正常, 1=最小化, 2=最大化")]
    public int WindowState { get; set; }

    [JsonPropertyName("window.position.x")]
    [Description("主窗口位置的 X 坐标")]
    public int WindowPositionX { get; set; }

    [JsonPropertyName("window.position.y")]
    [Description("主窗口位置的 Y 坐标")]
    public int WindowPositionY { get; set; }

    [JsonPropertyName("window.width")]
    [Description("主窗口宽度")]
    public double WindowWidth { get; set; }

    [JsonPropertyName("window.height")]
    [Description("主窗口高度")]
    public double WindowHeight { get; set; }
}

public partial class NotificationSettings : ObservableObject
{
    [ObservableProperty]
    [property: JsonPropertyName("enabled")]
    [property: Description("是否启用通知功能")]
    private bool _isEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("system.enabled")]
    [property: Description("是否启用系统通知")]
    private bool _isSystemEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("bark.enabled")]
    [property: Description("是否启用 Bark 推送")]
    private bool _isBarkEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("bark.ciphertext")]
    [property: Description("Bark 推送的密文内容，设置后作为 ciphertext 参数发送")]
    private string _barkCiphertext = "";

    [ObservableProperty]
    [property: JsonPropertyName("bark.deviceKey")]
    [property: Description("Bark 设备 Key，支持逗号分隔多个设备")]
    private string _barkDeviceKey = "";

    [ObservableProperty]
    [property: JsonPropertyName("bark.group")]
    [property: Description("Bark 消息分组")]
    private string _barkGroup = "StarRailAssistant";

    [ObservableProperty]
    [property: JsonPropertyName("bark.icon")]
    [property: Description("Bark 推送图标的 URL")]
    private string _barkIcon = "";

    [ObservableProperty]
    [property: JsonPropertyName("bark.level")]
    [property: Description("Bark 推送级别，active/timeSensitive/passive")]
    private string _barkLevel = "";

    [ObservableProperty]
    [property: JsonPropertyName("bark.serverUrl")]
    [property: Description("Bark 服务器地址")]
    private string _barkServerUrl = "https://api.day.app";

    [ObservableProperty]
    [property: JsonPropertyName("bark.sound")]
    [property: Description("Bark 推送提示音名称")]
    private string _barkSound = "";

    [ObservableProperty]
    [property: JsonPropertyName("dingTalk.enabled")]
    [property: Description("是否启用钉钉机器人推送")]
    private bool _isDingTalkEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("dingTalk.secret")]
    [property: Description("钉钉机器人的加签密钥（SEC 开头）")]
    private string _dingTalkSecret = "";

    [ObservableProperty]
    [property: JsonPropertyName("dingTalk.webhookUrl")]
    [property: Description("钉钉机器人的 Webhook 地址")]
    private string _dingTalkWebhookUrl = "";

    [ObservableProperty]
    [property: JsonPropertyName("discord.enabled")]
    [property: Description("是否启用 Discord 推送")]
    private bool _isDiscordEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("discord.sendImage")]
    [property: Description("是否在 Discord 推送中附带截图")]
    private bool _isDiscordSendImage;

    [ObservableProperty]
    [property: JsonPropertyName("discord.webhookUrl")]
    [property: Description("Discord 的 Webhook 地址")]
    private string _discordWebhookUrl = "";

    [ObservableProperty]
    [property: JsonPropertyName("feishu.enabled")]
    [property: Description("是否启用飞书推送")]
    private bool _isFeishuEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("feishu.appId")]
    [property: Description("飞书应用的 App ID")]
    private string _feishuAppId = "";

    [ObservableProperty]
    [property: JsonPropertyName("feishu.appSecret")]
    [property: Description("飞书应用的 App Secret")]
    private string _feishuAppSecret = "";

    [ObservableProperty]
    [property: JsonPropertyName("feishu.receiveId")]
    [property: Description("飞书消息接收者 ID")]
    private string _feishuReceiveId = "";

    [ObservableProperty]
    [property: JsonPropertyName("feishu.receiveIdType")]
    [property: Description("飞书接收者 ID 类型，如 open_id、user_id、union_id、chat_id")]
    private string _feishuReceiveIdType = "";

    [ObservableProperty]
    [property: JsonPropertyName("feishu.webhookUrl")]
    [property: Description("飞书机器人的 Webhook 地址")]
    private string _feishuWebhookUrl = "";

    [ObservableProperty]
    [property: JsonPropertyName("oneBot.enabled")]
    [property: Description("是否启用 OneBot 推送")]
    private bool _isOneBotEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("oneBot.sendImage")]
    [property: Description("是否在 OneBot 推送中附带截图")]
    private bool _isOneBotSendImage;

    [ObservableProperty]
    [property: JsonPropertyName("oneBot.groupId")]
    [property: Description("OneBot 推送的目标群号")]
    private string _oneBotGroupId = "";

    [ObservableProperty]
    [property: JsonPropertyName("oneBot.token")]
    [property: Description("OneBot 的访问 Token")]
    private string _oneBotToken = "";

    [ObservableProperty]
    [property: JsonPropertyName("oneBot.url")]
    [property: Description("OneBot 的 HTTP API 地址")]
    private string _oneBotUrl = "";

    [ObservableProperty]
    [property: JsonPropertyName("oneBot.userId")]
    [property: Description("OneBot 机器人的账号")]
    private string _oneBotUserId = "";

    [ObservableProperty]
    [property: JsonPropertyName("serverChan.enabled")]
    [property: Description("是否启用 Server酱 推送")]
    private bool _isServerChanEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("serverChan.sendKey")]
    [property: Description("Server酱 的 SendKey")]
    private string _serverChanSendKey = "";

    [ObservableProperty]
    [property: JsonPropertyName("telegram.enabled")]
    [property: Description("是否启用 Telegram 推送")]
    private bool _isTelegramEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("telegram.proxyEnabled")]
    [property: Description("是否为 Telegram 推送启用代理")]
    private bool _isTelegramProxyEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("telegram.sendImage")]
    [property: Description("是否在 Telegram 推送中附带截图")]
    private bool _isTelegramSendImage;

    [ObservableProperty]
    [property: JsonPropertyName("weCom.enabled")]
    [property: Description("是否启用企业微信推送")]
    private bool _isWeComEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("weCom.sendImage")]
    [property: Description("是否在企业微信推送中附带截图")]
    private bool _isWeComSendImage;

    [ObservableProperty]
    [property: JsonPropertyName("weCom.webhookUrl")]
    [property: Description("企业微信机器人的 Webhook 地址")]
    private string _weComWebhookUrl = "";

    [ObservableProperty]
    [property: JsonPropertyName("webhook.enabled")]
    [property: Description("是否启用自定义 Webhook 推送")]
    private bool _isWebhookEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("webhook.url")]
    [property: Description("自定义 Webhook 的 URL")]
    private string _webhookUrl = "";

    [ObservableProperty]
    [property: JsonPropertyName("xxtui.enabled")]
    [property: Description("是否启用 息知(xxtui) 推送")]
    private bool _isXxtuiEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("email.enabled")]
    [property: Description("是否启用邮件推送")]
    private bool _isEmailEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("email.smtpPort")]
    [property: Description("SMTP 服务器端口，SSL 通常为 465")]
    private int _smtpPort = 465;

    [ObservableProperty]
    [property: JsonPropertyName("email.smtpReceiver")]
    [property: Description("收件邮箱地址")]
    private string _smtpReceiver = "";

    [ObservableProperty]
    [property: JsonPropertyName("email.smtpSender")]
    [property: Description("发件邮箱地址")]
    private string _smtpSender = "";

    [ObservableProperty]
    [property: JsonPropertyName("email.smtpServer")]
    [property: Description("SMTP 服务器地址")]
    private string _smtpServer = "";

    [JsonPropertyName("email.smtpAuthCode")]
    [Description("SMTP 授权码（加密存储）")]
    public string EncryptedSmtpAuthCode { get; set; } = "";

    [ObservableProperty] [property: JsonIgnore]
    private string _smtpAuthCode = "";

    [ObservableProperty]
    [property: JsonPropertyName("telegram.apiBaseUrl")]
    [property: Description("Telegram Bot API 地址")]
    private string _telegramApiBaseUrl = "https://api.telegram.org";

    [ObservableProperty]
    [property: JsonPropertyName("telegram.botToken")]
    [property: Description("Telegram 机器人的 Bot Token")]
    private string _telegramBotToken = "";

    [ObservableProperty]
    [property: JsonPropertyName("telegram.chatId")]
    [property: Description("Telegram 推送目标 Chat ID")]
    private string _telegramChatId = "";

    [ObservableProperty]
    [property: JsonPropertyName("telegram.proxyUrl")]
    [property: Description("Telegram 代理服务器地址")]
    private string _telegramProxyUrl = "http://127.0.0.1:7890";

    [ObservableProperty]
    [property: JsonPropertyName("xxtui.apiKey")]
    [property: Description("息知(xxtui) 的 API Key")]
    private string _xxtuiApiKey = "";

    [ObservableProperty]
    [property: JsonPropertyName("xxtui.channel")]
    [property: Description("息知(xxtui) 的推送通道")]
    private string _xxtuiChannel = "";

    [ObservableProperty]
    [property: JsonPropertyName("xxtui.source")]
    [property: Description("息知(xxtui) 的消息来源")]
    private string _xxtuiSource = "";

    [ObservableProperty]
    [property: JsonPropertyName("onCompleted")]
    [property: Description("任务完成时发送通知的任务名称列表")]
    private ObservableCollection<string> _onCompleted = [];

    [ObservableProperty]
    [property: JsonPropertyName("onStart")]
    [property: Description("任务开始时发送通知的任务名称列表")]
    private ObservableCollection<string> _onStart = [];
}

public partial class UpdateSettings : ObservableObject
{
    [ObservableProperty]
    [property: JsonPropertyName("downloadChannel")]
    [property: Description("下载渠道，0=Mirror Chyan, 1=Github Release, 2=AUTO-MAS")]
    private int _downloadChannel;

    [ObservableProperty]
    [property: JsonPropertyName("autoUpdate")]
    [property: Description("是否启用自动更新: 将在有更新时直接开始下载")]
    private bool _isAutoUpdate;

    [ObservableProperty]
    [property: JsonPropertyName("checkForUpdates")]
    [property: Description("是否启用检查更新功能: 将在启动时检查更新并提示用户")]
    private bool _isCheckForUpdates = true;

    [ObservableProperty]
    [property: JsonIgnore]
    private string _mirrorChyanCdk = "";

    [ObservableProperty]
    [property: JsonPropertyName("updateChannel")]
    [property: Description("更新频道，0=Stable, 1=Beta")]
    private int _updateChannel;

    [ObservableProperty]
    [property: JsonPropertyName("downloadPath")]
    [property: Description("更新安装包的下载保存目录，留空则使用系统临时目录下的 SRA 文件夹")]
    private string _downloadPath = "";

    [JsonPropertyName("mirrorChyanCdk")]
    [Description("Mirror Chyan 下载渠道的授权码，敏感信息将被加密存储")]
    public string EncryptedMirrorChyanCdk { get; set; } = "";
}

public partial class AdvancedSettings : ObservableObject
{
    [ObservableProperty]
    [property: JsonPropertyName("backend.launchArgs")]
    [property: Description("后端启动参数")]
    [property: DefaultValue("--inline")]
    private string _backendLaunchArgs = "--inline";

    [ObservableProperty]
    [property: JsonPropertyName("backend.remote.enabled")]
    [property: Description("是否使用远程后端")]
    private bool _isRemoteEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("backend.remote.baseUrl")]
    [property: Description("远程后端地址")]
    private string _remoteBaseUrl = "http://localhost:5000";

    [ObservableProperty]
    [property: JsonPropertyName("developerMode.overlay")]
    [property: Description("是否在叠加层显示调试信息")]
    private bool _isDebugOverlayEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("developerMode.enabled")]
    [property: Description("是否启用开发者模式")]
    private bool _isDeveloperModeEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("developerMode.python.enabled")]
    [property: Description("是否启用 Python 后端")]
    private bool _isPythonEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("developerMode.saveOcrImage")]
    [property: Description("是否保存 OCR 截图以便调试")]
    private bool _isSaveOcrImage;

    [ObservableProperty]
    [property: JsonPropertyName("developerMode.python.main")]
    [property: Description("Python 后端主脚本路径，通常为 main.py")]
    private string _pythonMain = "";

    [ObservableProperty]
    [property: JsonPropertyName("developerMode.python.path")]
    [property: Description("Python 解释器路径，通常为 python.exe 的路径")]
    private string _pythonPath = "";
}

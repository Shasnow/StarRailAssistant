using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Text.Json.Serialization;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

public class AppSettings
{
    public const string Version = "2.17.0"; // 应用版本号

    [JsonPropertyName("general")] public GeneralSettings General { get; init; } = new();

    [JsonPropertyName("display")] public DisplaySettings Display { get; init; } = new();

    [JsonPropertyName("update")] public UpdateSettings Update { get; init; } = new();

    [JsonPropertyName("advanced")] public AdvancedSettings Advanced { get; init; } = new();

    [JsonPropertyName("notification")] public NotificationSettings Notification { get; init; } = new();
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
    private string _gameArgsFullScreenMode = "窗口化";

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.windowSize")]
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
    private bool _isCloudGameEnable;

    [ObservableProperty]
    [property: JsonPropertyName("cloudGame.browser")]
    [property: Description("云游戏使用的浏览器")]
    private string _cloudGameBrowser = "Microsoft Edge";

    [ObservableProperty] [property: JsonPropertyName("keybindings.e")]
    private string _hotkeyE = "E";

    [ObservableProperty] [property: JsonPropertyName("keybindings.f1")]
    private string _hotkeyF1 = "F1";

    [ObservableProperty] [property: JsonPropertyName("keybindings.f2")]
    private string _hotkeyF2 = "F2";

    [ObservableProperty] [property: JsonPropertyName("keybindings.f3")]
    private string _hotkeyF3 = "F3";

    [ObservableProperty] [property: JsonPropertyName("keybindings.f4")]
    private string _hotkeyF4 = "F4";

    [ObservableProperty] [property: JsonPropertyName("keybindings.stop")]
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
    [property: JsonPropertyName("language")]
    [property: Description("界面语言，0=中文, 2=English")]
    private int _language;

    [ObservableProperty]
    [property: JsonPropertyName("window.remember")]
    [property: Description("是否记住窗口位置和大小")]
    private bool _isRememberWindow;

    [JsonPropertyName("window.state")]
    [Description("窗口状态，0=正常, 1=最小化, 2=最大化")]
    public int WindowState { get; set; }

    [JsonPropertyName("window.position.x")]
    public int WindowPositionX { get; set; }

    [JsonPropertyName("window.position.y")]
    public int WindowPositionY { get; set; }

    [JsonPropertyName("window.width")] public double WindowWidth { get; set; }

    [JsonPropertyName("window.height")] public double WindowHeight { get; set; }
}

public partial class NotificationSettings : ObservableObject
{
    [ObservableProperty] [property: JsonPropertyName("enabled")]
    private bool _isEnabled;

    [ObservableProperty] [property: JsonPropertyName("system.enabled")]
    private bool _isSystemEnabled;

    [ObservableProperty] [property: JsonPropertyName("bark.enabled")]
    private bool _isBarkEnabled;

    [ObservableProperty] [property: JsonPropertyName("bark.ciphertext")]
    private string _barkCiphertext = "";

    [ObservableProperty] [property: JsonPropertyName("bark.deviceKey")]
    private string _barkDeviceKey = "";

    [ObservableProperty] [property: JsonPropertyName("bark.group")]
    private string _barkGroup = "StarRailAssistant";

    [ObservableProperty] [property: JsonPropertyName("bark.icon")]
    private string _barkIcon = "";

    [ObservableProperty] [property: JsonPropertyName("bark.level")]
    private string _barkLevel = "";

    [ObservableProperty] [property: JsonPropertyName("bark.serverUrl")]
    private string _barkServerUrl = "https://api.day.app";

    [ObservableProperty] [property: JsonPropertyName("bark.sound")]
    private string _barkSound = "";

    [ObservableProperty] [property: JsonPropertyName("dingTalk.enabled")]
    private bool _isDingTalkEnabled;

    [ObservableProperty] [property: JsonPropertyName("dingTalk.secret")]
    private string _dingTalkSecret = "";

    [ObservableProperty] [property: JsonPropertyName("dingTalk.webhookUrl")]
    private string _dingTalkWebhookUrl = "";

    [ObservableProperty] [property: JsonPropertyName("discord.enabled")]
    private bool _isDiscordEnabled;

    [ObservableProperty] [property: JsonPropertyName("discord.sendImage")]
    private bool _isDiscordSendImage;

    [ObservableProperty] [property: JsonPropertyName("discord.webhookUrl")]
    private string _discordWebhookUrl = "";

    [ObservableProperty] [property: JsonPropertyName("feishu.enabled")]
    private bool _isFeishuEnabled;

    [ObservableProperty] [property: JsonPropertyName("feishu.appId")]
    private string _feishuAppId = "";

    [ObservableProperty] [property: JsonPropertyName("feishu.appSecret")]
    private string _feishuAppSecret = "";

    [ObservableProperty] [property: JsonPropertyName("feishu.receiveId")]
    private string _feishuReceiveId = "";

    [ObservableProperty] [property: JsonPropertyName("feishu.receiveIdType")]
    private string _feishuReceiveIdType = "";

    [ObservableProperty] [property: JsonPropertyName("feishu.webhookUrl")]
    private string _feishuWebhookUrl = "";

    [ObservableProperty] [property: JsonPropertyName("oneBot.enabled")]
    private bool _isOneBotEnabled;

    [ObservableProperty] [property: JsonPropertyName("oneBot.sendImage")]
    private bool _isOneBotSendImage;

    [ObservableProperty] [property: JsonPropertyName("oneBot.groupId")]
    private string _oneBotGroupId = "";

    [ObservableProperty] [property: JsonPropertyName("oneBot.token")]
    private string _oneBotToken = "";

    [ObservableProperty] [property: JsonPropertyName("oneBot.url")]
    private string _oneBotUrl = "";

    [ObservableProperty] [property: JsonPropertyName("oneBot.userId")]
    private string _oneBotUserId = "";

    [ObservableProperty] [property: JsonPropertyName("serverChan.enabled")]
    private bool _isServerChanEnabled;

    [ObservableProperty] [property: JsonPropertyName("serverChan.sendKey")]
    private string _serverChanSendKey = "";

    [ObservableProperty] [property: JsonPropertyName("telegram.enabled")]
    private bool _isTelegramEnabled;

    [ObservableProperty] [property: JsonPropertyName("telegram.proxyEnabled")]
    private bool _isTelegramProxyEnabled;

    [ObservableProperty] [property: JsonPropertyName("telegram.sendImage")]
    private bool _isTelegramSendImage;

    [ObservableProperty] [property: JsonPropertyName("weCom.enabled")]
    private bool _isWeComEnabled;

    [ObservableProperty] [property: JsonPropertyName("weCom.sendImage")]
    private bool _isWeComSendImage;

    [ObservableProperty] [property: JsonPropertyName("weCom.webhookUrl")]
    private string _weComWebhookUrl = "";

    [ObservableProperty] [property: JsonPropertyName("webhook.enabled")]
    private bool _isWebhookEnabled;

    [ObservableProperty] [property: JsonPropertyName("webhook.url")]
    private string _webhookUrl = "";

    [ObservableProperty] [property: JsonPropertyName("xxtui.enabled")]
    private bool _isXxtuiEnabled;

    [ObservableProperty] [property: JsonPropertyName("email.enabled")]
    private bool _isEmailEnabled;

    [ObservableProperty] [property: JsonPropertyName("email.smtpPort")]
    private int _smtpPort = 465;

    [ObservableProperty] [property: JsonPropertyName("email.smtpReceiver")]
    private string _smtpReceiver = "";

    [ObservableProperty] [property: JsonPropertyName("email.smtpSender")]
    private string _smtpSender = "";

    [ObservableProperty] [property: JsonPropertyName("email.smtpServer")]
    private string _smtpServer = "";

    [JsonPropertyName("email.smtpAuthCode")]
    public string EncryptedSmtpAuthCode { get; set; } = "";

    [ObservableProperty] [property: JsonIgnore]
    private string _smtpAuthCode = "";

    [ObservableProperty] [property: JsonPropertyName("telegram.apiBaseUrl")]
    private string _telegramApiBaseUrl = "https://api.telegram.org";

    [ObservableProperty] [property: JsonPropertyName("telegram.botToken")]
    private string _telegramBotToken = "";

    [ObservableProperty] [property: JsonPropertyName("telegram.chatId")]
    private string _telegramChatId = "";

    [ObservableProperty] [property: JsonPropertyName("telegram.proxyUrl")]
    private string _telegramProxyUrl = "http://127.0.0.1:7890";

    [ObservableProperty] [property: JsonPropertyName("xxtui.apiKey")]
    private string _xxtuiApiKey = "";

    [ObservableProperty] [property: JsonPropertyName("xxtui.channel")]
    private string _xxtuiChannel = "";

    [ObservableProperty] [property: JsonPropertyName("xxtui.source")]
    private string _xxtuiSource = "";
    
    [ObservableProperty] [property: JsonPropertyName("onCompleted")]
    private ObservableCollection<string> _onCompleted = [];

    [ObservableProperty] [property: JsonPropertyName("onStart")]
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
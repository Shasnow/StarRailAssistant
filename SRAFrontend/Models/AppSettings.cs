using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Text.Json.Serialization;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

public class AppSettings
{
    [JsonPropertyName("general")] 
    public GeneralSettings General { get; set; } = new();

    [JsonPropertyName("display")]
    public DisplaySettings Display { get; set; } = new();

    [JsonPropertyName("update")]
    public UpdateSettings Update { get; set; } = new();

    [JsonPropertyName("advanced")]
    public AdvancedSettings Advanced { get; set; } = new();

    [JsonPropertyName("notification")]
    public NotificationSettings Notification { get; set; } = new();
    
    public const string Version = "2.13.0-beta.1"; // 应用版本号
}

public partial class GeneralSettings : ObservableObject
{
    [ObservableProperty]
    [property: JsonPropertyName("gamePath.uris")]
    private ObservableCollection<string> _gamePaths = [];

    [ObservableProperty]
    [property: JsonPropertyName("gamePath.index")]
    private int _gamePathIndex;

    [ObservableProperty]
    [property: JsonPropertyName("gamePath.autoDetect")]
    private bool _isAutoDetectGamePath = true;

    [ObservableProperty]
    [property: JsonPropertyName("cloudGame.enabled")]
    private bool _isCloudGameEnable;
    
    [ObservableProperty]
    [property: JsonPropertyName("templateMatchConfidence")]
    private double _templateMatchConfidence = 0.9;

    [ObservableProperty]
    [property: JsonPropertyName("overlay.enabled")]
    private bool _isOverlayEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.enabled")]
    private bool _isGameArgsEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.windowSize")]
    private string _gameArgsWindowSize = "1920x1080";

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.fullScreenMode")]
    private string _gameArgsFullScreenMode = "窗口化";

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.popupWindow")]
    private bool _isGameArgsPopupWindow;

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.advanced")]
    private string _gameArgsAdvanced = "";

    [ObservableProperty]
    [property: JsonPropertyName("gameArgs.useCmd")]
    private bool _isUseCmd;

    [ObservableProperty]
    [property: JsonPropertyName("keybindings.stop")]
    private string _hotkeyStop = "F9";

    [ObservableProperty]
    [property: JsonPropertyName("keybindings.f1")]
    private string _hotkeyF1 = "F1";

    [ObservableProperty]
    [property: JsonPropertyName("keybindings.f2")]
    private string _hotkeyF2 = "F2";

    [ObservableProperty]
    [property: JsonPropertyName("keybindings.f3")]
    private string _hotkeyF3 = "F3";

    [ObservableProperty]
    [property: JsonPropertyName("keybindings.f4")]
    private string _hotkeyF4 = "F4";
    
    [ObservableProperty]
    [property: JsonPropertyName("keybindings.m")]
    private string _hotkeyM = "M";
    
    [ObservableProperty]
    [property: JsonPropertyName("keybindings.e")]
    private string _hotkeyE = "E";
}

public partial class DisplaySettings : ObservableObject
{
    [ObservableProperty]
    [property: JsonPropertyName("backgroundImage.uri")]
    private string _backgroundImageUri = "";

    [ObservableProperty]
    [property: JsonPropertyName("backgroundImage.opacity")]
    private double _backgroundOpacity = 1;

    [ObservableProperty]
    [property: JsonPropertyName("controlPanel.opacity")]
    private double _controlPanelOpacity = 0.9;

    [ObservableProperty]
    [property: JsonPropertyName("language")]
    private int _language;
}

public partial class NotificationSettings : ObservableObject
{
    [ObservableProperty]
    [property: JsonPropertyName("enabled")]
    private bool _isEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("system.enabled")]
    private bool _isSystemEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("email.enabled")]
    private bool _isEmailEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("email.smtpServer")]
    private string _smtpServer = "";

    [ObservableProperty]
    [property: JsonPropertyName("email.smtpPort")]
    private int _smtpPort = 465;

    [ObservableProperty]
    [property: JsonPropertyName("email.smtpSender")]
    private string _smtpSender = "";

    [ObservableProperty]
    [property: JsonIgnore]
    private string _smtpAuthCode = "";
    [JsonPropertyName("email.smtpAuthCode")]
    public string EncryptedSmtpAuthCode {get; set;} = "";

    [ObservableProperty]
    [property: JsonPropertyName("email.smtpReceiver")]
    private string _smtpReceiver = "";

    [ObservableProperty]
    [property: JsonPropertyName("webhook.enabled")]
    private bool _isWebhookEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("webhook.url")]
    private string _webhookUrl = "";

    [ObservableProperty]
    [property: JsonPropertyName("telegram.enabled")]
    private bool _isTelegramEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("telegram.botToken")]
    private string _telegramBotToken = "";

    [ObservableProperty]
    [property: JsonPropertyName("telegram.chatId")]
    private string _telegramChatId = "";

    [ObservableProperty]
    [property: JsonPropertyName("telegram.proxyEnabled")]
    private bool _isTelegramProxyEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("telegram.proxyUrl")]
    private string _telegramProxyUrl = "http://127.0.0.1:7890";

    [ObservableProperty]
    [property: JsonPropertyName("telegram.apiBaseUrl")]
    private string _telegramApiBaseUrl = "https://api.telegram.org";

    [ObservableProperty]
    [property: JsonPropertyName("telegram.sendImage")]
    private bool _isTelegramSendImage;

    [ObservableProperty]
    [property: JsonPropertyName("serverChan.enabled")]
    private bool _isServerChanEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("serverChan.sendKey")]
    private string _serverChanSendKey = "";

    [ObservableProperty]
    [property: JsonPropertyName("oneBot.enabled")]
    private bool _isOneBotEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("oneBot.url")]
    private string _oneBotUrl = "";

    [ObservableProperty]
    [property: JsonPropertyName("oneBot.userId")]
    private string _oneBotUserId = "";

    [ObservableProperty]
    [property: JsonPropertyName("oneBot.groupId")]
    private string _oneBotGroupId = "";

    [ObservableProperty]
    [property: JsonPropertyName("oneBot.token")]
    private string _oneBotToken = "";

    [ObservableProperty]
    [property: JsonPropertyName("oneBot.sendImage")]
    private bool _isOneBotSendImage;

    [ObservableProperty]
    [property: JsonPropertyName("bark.enabled")]
    private bool _isBarkEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("bark.serverUrl")]
    private string _barkServerUrl = "https://api.day.app";

    [ObservableProperty]
    [property: JsonPropertyName("bark.deviceKey")]
    private string _barkDeviceKey = "";
    
    [ObservableProperty]
    [property: JsonPropertyName("bark.group")]
    private string _barkGroup = "StarRailAssistant";
    
    [ObservableProperty]
    [property: JsonPropertyName("bark.level")]
    private string _barkLevel = "";
    
    [ObservableProperty]
    [property: JsonPropertyName("bark.sound")]
    private string _barkSound = "";

    [ObservableProperty]
    [property: JsonPropertyName("bark.icon")]
    private string _barkIcon = "";

    [ObservableProperty]
    [property: JsonPropertyName("bark.ciphertext")]
    private string _barkCiphertext = "";

    [ObservableProperty]
    [property: JsonPropertyName("feishu.enabled")]
    private bool _isFeishuEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("feishu.webhookUrl")]
    private string _feishuWebhookUrl = "";

    [ObservableProperty]
    [property: JsonPropertyName("feishu.appId")]
    private string _feishuAppId = "";

    [ObservableProperty]
    [property: JsonPropertyName("feishu.appSecret")]
    private string _feishuAppSecret = "";

    [ObservableProperty]
    [property: JsonPropertyName("feishu.receiveId")]
    private string _feishuReceiveId = "";

    [ObservableProperty]
    [property: JsonPropertyName("feishu.receiveIdType")]
    private string _feishuReceiveIdType = "";

    [ObservableProperty]
    [property: JsonPropertyName("weCom.enabled")]
    private bool _isWeComEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("weCom.webhookUrl")]
    private string _weComWebhookUrl = "";

    [ObservableProperty]
    [property: JsonPropertyName("weCom.sendImage")]
    private bool _isWeComSendImage;

    [ObservableProperty]
    [property: JsonPropertyName("dingTalk.enabled")]
    private bool _isDingTalkEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("dingTalk.webhookUrl")]
    private string _dingTalkWebhookUrl = "";

    [ObservableProperty]
    [property: JsonPropertyName("dingTalk.secret")]
    private string _dingTalkSecret = "";

    [ObservableProperty]
    [property: JsonPropertyName("discord.enabled")]
    private bool _isDiscordEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("discord.webhookUrl")]
    private string _discordWebhookUrl = "";

    [ObservableProperty]
    [property: JsonPropertyName("discord.sendImage")]
    private bool _isDiscordSendImage;

    [ObservableProperty]
    [property: JsonPropertyName("xxtui.enabled")]
    private bool _isXxtuiEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("xxtui.apiKey")]
    private string _xxtuiApiKey = "";

    [ObservableProperty]
    [property: JsonPropertyName("xxtui.source")]
    private string _xxtuiSource = "";

    [ObservableProperty]
    [property: JsonPropertyName("xxtui.channel")]
    private string _xxtuiChannel = "";

    [ObservableProperty]
    [property: JsonPropertyName("onStart")]
    private List<string> _onStart = [];

    [ObservableProperty]
    [property: JsonPropertyName("onComplete")]
    private List<string> _onComplete = [];
}

public partial class UpdateSettings : ObservableObject
{
    [ObservableProperty]
    [property: JsonPropertyName("checkForUpdates")]
    private bool _isCheckForUpdates = true;

    [ObservableProperty]
    [property: JsonPropertyName("autoUpdate")]
    private bool _isAutoUpdate;

    [ObservableProperty]
    [property: JsonIgnore]
    private string _mirrorChyanCdk = "";

    [JsonPropertyName("mirrorChyanCdk")]
    public string EncryptedMirrorChyanCdk { get; set; } = "";

    [ObservableProperty]
    [property: JsonPropertyName("downloadChannel")]
    private int _downloadChannel;

    [ObservableProperty]
    [property: JsonPropertyName("updateChannel")]
    private int _updateChannel;
}

public partial class AdvancedSettings : ObservableObject
{
    [ObservableProperty]
    [property: JsonPropertyName("backendLaunchArgs")]
    private string _backendLaunchArgs = "";

    [ObservableProperty]
    [property: JsonPropertyName("developerMode.enabled")]
    private bool _isDeveloperModeEnabled;
    
    [ObservableProperty]
    [property: JsonPropertyName("developerMode.saveOcrImage")]
    private bool _isSaveOcrImage;
    
    [ObservableProperty]
    [property: JsonPropertyName("developerMode.overlay")]
    private bool _isDebugOverlayEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("developerMode.usePython")]
    private bool _isUsePython;

    [ObservableProperty]
    [property: JsonPropertyName("developerMode.pythonPath")]
    private string _pythonPath = "";

    [ObservableProperty]
    [property: JsonPropertyName("developerMode.pythonMain")]
    private string _pythonMain = "";
}
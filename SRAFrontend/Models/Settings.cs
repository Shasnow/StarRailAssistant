using System.Text.Json.Serialization;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

public partial class Settings : ObservableObject
{
    [ObservableProperty] private bool _allowEmailNotifications; // 是否允许邮件通知
    [ObservableProperty] private bool _allowNotifications = true; // 是否允许通知
    [ObservableProperty] private bool _allowSystemNotifications = true; // 是否允许系统通知
    [ObservableProperty] private int _appChannel; // 0: stable, 1: beta
    [ObservableProperty] private bool _isOverlayEnabled; // 是否启用叠加层
    [ObservableProperty] private bool _isOverlayDebugInfoEnabled; // 是否启用叠加层鼠标信息

    [ObservableProperty] private double _backgroundOpacity = 0.9; // 背景图不透明度
    [ObservableProperty] private double _ctrlPanelOpacity = 0.9; // 控制面板不透明度
    [ObservableProperty] private string _backgroundImagePath = ""; // 背景图路径
    [ObservableProperty] private double _confidenceThreshold = 0.9; // 识图置信度阈值
    [ObservableProperty] private int _defaultPage; // 启动时默认页面索引
    [ObservableProperty] private int _downloadChannel; // 0: Mirror, 1: GitHub
    [ObservableProperty] private string _emailReceiver = ""; // 接收邮件地址
    [ObservableProperty] private string _emailSender = ""; // 发送邮件地址
    [ObservableProperty] private bool _enableAutoUpdate = true; // 是否启用自动更新
    [ObservableProperty] private bool _enableMinimizeToTray; // 是否启用最小化到托盘
    [ObservableProperty] private bool _enableStartupLaunch; // 是否启用开机自启动
    [ObservableProperty] private int _language; // 0: 简体中文, 1: English

    [ObservableProperty] [property: JsonIgnore]
    private string _mirrorChyanCdk = "";
    [ObservableProperty] [property: JsonIgnore]
    private string _emailAuthCode = ""; // 邮件授权码

    [ObservableProperty] private int _smtpPort = 465; // SMTP服务器端口

    [ObservableProperty] private string _smtpServer = "smtp.qq.com"; // SMTP服务器地址

    [ObservableProperty] private bool _isAutoDetectGamePath = true; // 是否自动检测游戏安装路径

    [ObservableProperty] private int _gamePathIndex; // 游戏安装路径
    public AvaloniaList<string> GamePaths { get; set; } = []; // 可能的游戏安装路径列表

    // 启动参数配置
    [ObservableProperty] private bool _launchArgumentsEnabled = true; // 是否启用启动参数
    [ObservableProperty] private string _launchArgumentsScreenSize = "1920x1080"; // 窗口尺寸
    [ObservableProperty] private string _launchArgumentsFullScreenMode = "窗口化"; // 显示模式 (窗口化/全屏)
    [ObservableProperty] private bool _launchArgumentsPopupWindow; // 是否无边框窗口
    [ObservableProperty] private string _launchArgumentsAdvanced = ""; // 高级参数
    [ObservableProperty] private bool _launchWithCmd; // 使用 CMD 启动游戏
    
    // 高级
    [ObservableProperty] private string _backendArguments = "--inline"; // 后端启动参数
    
    // 开发者模式
    [ObservableProperty] private bool _isDeveloperMode; // 开发者模式
    [ObservableProperty] private bool _isSaveOcrImage; // 是否保存OCR截图
    [ObservableProperty] private bool _isUsingPython; // 是否使用Python版本后端
    [ObservableProperty] private string _pythonPath = ""; // Python解释器路径
    [ObservableProperty] private string _pythonMainPy = ""; // Python主程序路径

    [JsonPropertyName("MirrorChyanCdk")] public string EncryptedMirrorChyanCdk { get; set; } = "";
    [JsonPropertyName("EmailAuthCode")] public string EncryptedEmailAuthCode { get; set; } = "";

    // 快捷键设置
    public string ActivityHotkey { get; set; } = "F1"; // 活动 默认 F1
    public string ChronicleHotkey { get; set; } = "F2"; // 纪行 默认 F2
    public string WarpHotkey { get; set; } = "F3"; // 卡池 默认 F3
    public string GuideHotkey { get; set; } = "F4"; // 指南 默认 F4
    public string MapHotkey { get; set; } = "M"; // 地图 默认 M
    public string TechniqueHotkey { get; set; } = "E"; // 秘技 默认 E
    public string StartStopHotkey { get; set; } = "F9"; // 启动/停止 默认 F9

    // Webhook 通知
    [ObservableProperty] private bool _allowWebhookNotifications;
    [ObservableProperty] private string _webhookEndpoint = "";

    // Telegram 通知
    [ObservableProperty] private bool _allowTelegramNotifications;
    [ObservableProperty] private string _telegramBotToken = "";
    [ObservableProperty] private string _telegramChatId = "";
    [ObservableProperty] private bool _telegramProxyEnabled;
    [ObservableProperty] private string _telegramProxyUrl = "http://127.0.0.1:7890";
    [ObservableProperty] private string _telegramApiBaseUrl = "";
    [ObservableProperty] private bool _telegramSendImage;

    // ServerChan 通知
    [ObservableProperty] private bool _allowServerChanNotifications;
    [ObservableProperty] private string _serverChanSendKey = "";

    // OneBot 通知
    [ObservableProperty] private bool _allowOneBotNotifications;
    [ObservableProperty] private string _oneBotEndpoint = "";
    [ObservableProperty] private string _oneBotUserId = "";
    [ObservableProperty] private string _oneBotGroupId = "";
    [ObservableProperty] private string _oneBotToken = "";
    [ObservableProperty] private bool _oneBotSendImage;

    // Bark 通知
    [ObservableProperty] private bool _allowBarkNotifications;
    [ObservableProperty] private string _barkDeviceKey = "";
    [ObservableProperty] private string _barkServerUrl = "https://api.day.app";
    [ObservableProperty] private string _barkLevel = "";
    [ObservableProperty] private string _barkSound = "";
    [ObservableProperty] private string _barkGroup = "StarRailAssistant";
    [ObservableProperty] private string _barkIcon = "";
    [ObservableProperty] private string _barkCiphertext = "";

    // 飞书通知
    [ObservableProperty] private bool _allowFeishuNotifications;
    [ObservableProperty] private string _feishuWebhookUrl = "";
    [ObservableProperty] private string _feishuAppId = "";
    [ObservableProperty] private string _feishuAppSecret = "";
    [ObservableProperty] private string _feishuReceiveId = "";
    [ObservableProperty] private string _feishuReceiveIdType = "open_id";

    // 企业微信通知
    [ObservableProperty] private bool _allowWeComNotifications;
    [ObservableProperty] private string _weComWebhookUrl = "";
    [ObservableProperty] private bool _weComSendImage;

    // 钉钉通知
    [ObservableProperty] private bool _allowDingTalkNotifications;
    [ObservableProperty] private string _dingTalkWebhookUrl = "";
    [ObservableProperty] private string _dingTalkSecret = "";

    // Discord 通知
    [ObservableProperty] private bool _allowDiscordNotifications;
    [ObservableProperty] private string _discordWebhookUrl = "";
    [ObservableProperty] private bool _discordSendImage;

    // xxtui 通知
    [ObservableProperty] private bool _allowXxtuiNotifications;
    [ObservableProperty] private string _xxtuiApiKey = "";
    [ObservableProperty] private string _xxtuiSource = "";
    [ObservableProperty] private string _xxtuiChannel = "";

    // 任务通知配置（每个任务的开始/完成通知开关）
    [ObservableProperty] private bool _startGameTaskNotifyOnStart;
    [ObservableProperty] private bool _startGameTaskNotifyOnComplete;
    [ObservableProperty] private bool _trailblazePowerTaskNotifyOnStart;
    [ObservableProperty] private bool _trailblazePowerTaskNotifyOnComplete;
    [ObservableProperty] private bool _receiveRewardsTaskNotifyOnStart;
    [ObservableProperty] private bool _receiveRewardsTaskNotifyOnComplete;
    [ObservableProperty] private bool _cosmicStrifeTaskNotifyOnStart;
    [ObservableProperty] private bool _cosmicStrifeTaskNotifyOnComplete;
    [ObservableProperty] private bool _missionAccomplishTaskNotifyOnStart;
    [ObservableProperty] private bool _missionAccomplishTaskNotifyOnComplete;

}
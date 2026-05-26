using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Threading.Tasks;
using Avalonia.Collections;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Platform.Storage;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Data;
using SRAFrontend.Localization;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;

public partial class SettingsPageViewModel : PageViewModel
{
    private readonly IBackendService _backendService;
    private readonly CacheService _cacheService;
    private readonly CommonModel _commonModel;
    private readonly AvaloniaList<CustomizableKey> _customizableKeys;
    private readonly OverlayService _overlayService;
    private readonly RegistryService _registryService;

    private readonly SettingsService _settingsService;
    private readonly UpdateService _updateService;

    /// <inheritdoc />
    public SettingsPageViewModel(
        SettingsService settingsService,
        UpdateService updateService,
        CacheService cacheService,
        CommonModel commonModel,
        RegistryService registryService,
        IBackendService backendService,
        OverlayService overlayService) : base(PageName.Setting,
        "\uE272")
    {
        _settingsService = settingsService;
        _updateService = updateService;
        _cacheService = cacheService;
        _registryService = registryService;
        _commonModel = commonModel;
        _backendService = backendService;
        _overlayService = overlayService;
        // 任务通用设置中的 启动/停止 快捷键（非游戏内快捷键分组）
        StartStopKey = new CustomizableKey(ListenKeyFor)
        {
            IconText = "\uE3E4",
            DisplayText = Resources.StopHotkeyText,
            DefaultKey = "F9"
        }.Bind(() => Settings.General.HotkeyStop,
            value => Settings.General.HotkeyStop = value);

        _customizableKeys =
        [
            new CustomizableKey(ListenKeyFor)
            {
                IconText = "\uE1F6",
                DisplayText = Resources.ActivityText,
                DefaultKey = "F1"
            }.Bind(() => Settings.General.HotkeyF1,
                value => Settings.General.HotkeyF1 = value),
            new CustomizableKey(ListenKeyFor)
            {
                IconText = "\uE320",
                DisplayText = Resources.ChronicleText,
                DefaultKey = "F2"
            }.Bind(() => Settings.General.HotkeyF2,
                value => Settings.General.HotkeyF2 = value),
            new CustomizableKey(ListenKeyFor)
            {
                IconText = "\uE77E",
                DisplayText = Resources.WarpText,
                DefaultKey = "F3"
            }.Bind(() => Settings.General.HotkeyF3,
                value => Settings.General.HotkeyF3 = value),
            new CustomizableKey(ListenKeyFor)
            {
                IconText = "\uE0E4",
                DisplayText = Resources.GuideText,
                DefaultKey = "F4"
            }.Bind(() => Settings.General.HotkeyF4,
                value => Settings.General.HotkeyF4 = value),
            new CustomizableKey(ListenKeyFor)
            {
                IconText = "\uE5E4",
                DisplayText = Resources.TechniqueText,
                DefaultKey = "E"
            }.Bind(() => Settings.General.HotkeyE,
                value => Settings.General.HotkeyE = value)
        ];

        DetectGamePath();
        SetGameResolution();
        if (IsOverlayEnabled) _overlayService.ShowOverlay();
        _overlayService.SetOverlayDebugInfoEnabled(Settings.Advanced.IsDebugOverlayEnabled);

        _settingsService.SettingsPropertyChanged += OnSettingsPropertyChanged;
    }

    public IAvaloniaReadOnlyList<CustomizableKey> CustomizableKeys => _customizableKeys;
    public CustomizableKey StartStopKey { get; }

    private AppSettings Settings => _settingsService.Settings;
    public GeneralSettings GeneralSettings => Settings.General;
    public DisplaySettings DisplaySettings => Settings.Display;
    public NotificationSettings NotificationSettings => Settings.Notification;
    public UpdateSettings UpdateSettings => Settings.Update;
    public AdvancedSettings AdvancedSettings => Settings.Advanced;
    public Cache Cache => _cacheService.Cache;
    public static string VersionText => AppSettings.Version;

    #region 任务通知配置
    // 启动游戏
    public bool StartGameOnStart
    {
        get => Settings.Notification.OnStart.Contains("StartGameTask");
        set => ToggleNotification("StartGameTask", value, Settings.Notification.OnStart);
    }
    
    public bool StartGameOnComplete
    {
        get => Settings.Notification.OnCompleted.Contains("StartGameTask");
        set => ToggleNotification("StartGameTask", value, Settings.Notification.OnCompleted);
    }
    
    // 清体力
    public bool TrailblazePowerOnStart
    {
        get => Settings.Notification.OnStart.Contains("TrailblazePowerTask");
        set => ToggleNotification("TrailblazePowerTask", value, Settings.Notification.OnStart);
    }
    
    public bool TrailblazePowerOnComplete
    {
        get => Settings.Notification.OnCompleted.Contains("TrailblazePowerTask");
        set => ToggleNotification("TrailblazePowerTask", value, Settings.Notification.OnCompleted);
    }
    
    // 领取奖励
    public bool ReceiveRewardsOnStart
    {
        get => Settings.Notification.OnStart.Contains("ReceiveRewardsTask");
        set => ToggleNotification("ReceiveRewardsTask", value, Settings.Notification.OnStart);
    }
    
    public bool ReceiveRewardsOnComplete
    {
        get => Settings.Notification.OnCompleted.Contains("ReceiveRewardsTask");
        set => ToggleNotification("ReceiveRewardsTask", value, Settings.Notification.OnCompleted);
    }
    
    // 旷宇纷争
    public bool CosmicStrifeOnStart
    {
        get => Settings.Notification.OnStart.Contains("CosmicStrifeTask");
        set => ToggleNotification("CosmicStrifeTask", value, Settings.Notification.OnStart);
    }
    
    public bool CosmicStrifeOnComplete
    {
        get => Settings.Notification.OnCompleted.Contains("CosmicStrifeTask");
        set => ToggleNotification("CosmicStrifeTask", value, Settings.Notification.OnCompleted);
    }
    
    // 任务完成
    public bool MissionAccomplishOnStart
    {
        get => Settings.Notification.OnStart.Contains("MissionAccomplishTask");
        set => ToggleNotification("MissionAccomplishTask", value, Settings.Notification.OnStart);
    }
    
    public bool MissionAccomplishOnComplete
    {
        get => Settings.Notification.OnCompleted.Contains("MissionAccomplishTask");
        set => ToggleNotification("MissionAccomplishTask", value, Settings.Notification.OnCompleted);
    }
    
    private void ToggleNotification(string taskName, bool value, ObservableCollection<string> collection)
    {
        if (value)
        {
            if (!collection.Contains(taskName))
                collection.Add(taskName);
        }
        else
        {
            collection.Remove(taskName);
        }
    }
    #endregion

    public string MirrorChyanCdk
    {
        get => Settings.Update.MirrorChyanCdk;
        set
        {
            // 先更新存储的值（即使后续验证失败，也保留用户输入便于修改）
            Settings.Update.MirrorChyanCdk = value;
            if (value == "")
            {
                Cache.CdkStatus = "";
                Cache.CdkStatusForeground = "#F5222D";
                return;
            }

            // 基础长度校验
            if (value.Length != 24)
            {
                Cache.CdkStatus = "CDK长度错误，应为24位字符";
                Cache.CdkStatusForeground = "#F5222D";
                return;
            }

            // 长度正确时，触发异步验证（不阻塞setter）
            _ = VerifyCdkAsync(); // 使用_忽略未等待的Task（需确保异常处理）
        }
    }

    public TopLevel? TopLevelObject { get; set; }

    public bool IsOverlayEnabled
    {
        get => Settings.General.IsOverlayEnabled;
        set
        {
            Settings.General.IsOverlayEnabled = value;
            if (value)
                _overlayService.ShowOverlay();
            else
                _overlayService.CloseOverlay();
        }
    }

    public bool IsOverlayDebugInfoEnabled
    {
        get => Settings.Advanced.IsDebugOverlayEnabled;
        set
        {
            Settings.Advanced.IsDebugOverlayEnabled = value;
            _overlayService.SetOverlayDebugInfoEnabled(value);
        }
    }

    [RelayCommand]
    private async Task VerifyCdkAsync()
    {
        var cdk = MirrorChyanCdk;
        // 显示"验证中"状态
        Cache.CdkStatus = "验证中...";
        Cache.CdkStatusForeground = "#FAAD14"; // 黄色表示处理中

        // 执行异步验证
        var response = await _updateService.VerifyCdkAsync(cdk);

        if (response is null)
        {
            Cache.CdkStatus = "验证失败，无法连接到验证服务";
            Cache.CdkStatusForeground = "#F5222D"; // 红色表示错误
            return;
        }

        if (response.Code == 0)
        {
            var leastTime = DateTimeOffset.FromUnixTimeSeconds(response.Data.CdkExpiredTime);
            Cache.CdkStatus = $"CDK有效 至: {leastTime:yyyy-MM-dd HH:mm:ss}";
            Cache.CdkStatusForeground = "#279F27"; // 绿色表示成功
        }
        else
        {
            Cache.CdkStatus = _updateService.GetErrorMessage(response.Code);
            Cache.CdkStatusForeground = "#F5222D"; // 红色表示错误
        }
    }

    [RelayCommand]
    private void CheckForUpdates()
    {
        _ = _commonModel.CheckForUpdatesAsync();
    }

    [RelayCommand]
    private void CreateDesktopShortcut()
    {
        _ = _commonModel.CheckDesktopShortcut(true);
    }

    [RelayCommand]
    private void OpenFolder(string folder)
    {
        var folderPath = folder switch
        {
            "backendLogs" => PathString.BackendLogsDir,
            "frontendLogs" => PathString.FrontendLogsDir,
            "configs" => PathString.ConfigsDir,
            "appdata" => PathString.AppDataDir,
            _ => "."
        };
        _commonModel.OpenFolderInExplorer(folderPath);
    }

    [RelayCommand]
    private async Task SelectedPath()
    {
        if (TopLevelObject is null) return;
        var files = await TopLevelObject.StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions());
        if (files.Count == 0) return;
        var localPath = files[0].Path.LocalPath;
        Settings.General.GamePaths.Add(localPath);
        Settings.General.GamePathIndex = Settings.General.GamePaths.Count - 1; // 切换到新添加的路径
    }

    [RelayCommand]
    private void DetectGamePath()
    {
        if (!Settings.General.IsAutoDetectGamePath) return;
        Settings.General.GamePaths.Clear();
        foreach (var gameInstallPath in _registryService.GetGameInstallPaths())
            Settings.General.GamePaths.Add(gameInstallPath);
        Settings.General.GamePathIndex = 0; // 切换到第一个路径
    }

    private void SetGameResolution()
    {
        if (!Settings.General.IsGameArgsEnabled) return;
        _registryService.SetTargetPcResolution();
    }

    private void OnSettingsPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName is nameof(Settings.General.GameArgsWindowSize)
            or nameof(Settings.General.GameArgsFullScreenMode))
            SetGameResolution();
    }

    #region 通知测试

    [RelayCommand]
    private void TestEmail()
    {
        SendTestNotification(
            "邮件测试",
            () => !string.IsNullOrEmpty(Settings.Notification.SmtpServer.Trim()) &&
                  Settings.Notification.SmtpPort > 0 &&
                  !string.IsNullOrEmpty(Settings.Notification.SmtpSender.Trim()) &&
                  !string.IsNullOrEmpty(Settings.Notification.SmtpAuthCode.Trim()) &&
                  !string.IsNullOrEmpty(Settings.Notification.SmtpReceiver.Trim()),
            "请先完成 SMTP 相关设置",
            "notify test email",
            "测试邮件已发送，请检查收件箱");
    }

    [RelayCommand]
    private void TestWebhook()
    {
        SendTestNotification(
            "Webhook 测试",
            () => !string.IsNullOrEmpty(Settings.Notification.WebhookUrl.Trim()),
            "请先填写 Webhook 地址",
            "notify test webhook",
            $"测试请求已发送至：{Settings.Notification.WebhookUrl.Trim()}");
    }

    [RelayCommand]
    private void TestTelegram()
    {
        SendTestNotification(
            "Telegram 测试",
            () => !string.IsNullOrEmpty(Settings.Notification.TelegramBotToken.Trim()) &&
                  !string.IsNullOrEmpty(Settings.Notification.TelegramChatId.Trim()),
            "请先填写 Bot Token 和 Chat ID",
            "notify test telegram",
            "测试消息已发送，请检查 Telegram");
    }

    [RelayCommand]
    private void TestServerChan()
    {
        SendTestNotification(
            "ServerChan 测试",
            () => !string.IsNullOrEmpty(Settings.Notification.ServerChanSendKey.Trim()),
            "请先填写 SendKey",
            "notify test serverchan",
            "测试消息已发送，请检查微信");
    }

    [RelayCommand]
    private void TestBark()
    {
        SendTestNotification(
            "Bark 测试",
            () => !string.IsNullOrEmpty(Settings.Notification.BarkDeviceKey.Trim()),
            "请先填写设备 Key",
            "notify test bark",
            "测试消息已发送，请检查 iPhone");
    }

    [RelayCommand]
    private void TestFeishu()
    {
        SendTestNotification(
            "飞书测试",
            () => !string.IsNullOrEmpty(Settings.Notification.FeishuWebhookUrl.Trim()),
            "请先填写 Webhook 地址",
            "notify test feishu",
            "测试消息已发送，请检查飞书");
    }

    [RelayCommand]
    private void TestWeCom()
    {
        SendTestNotification(
            "企业微信测试",
            () => !string.IsNullOrEmpty(Settings.Notification.WeComWebhookUrl.Trim()),
            "请先填写 Webhook 地址",
            "notify test wecom",
            "测试消息已发送，请检查企业微信");
    }

    [RelayCommand]
    private void TestDingTalk()
    {
        SendTestNotification(
            "钉钉测试",
            () => !string.IsNullOrEmpty(Settings.Notification.DingTalkWebhookUrl.Trim()),
            "请先填写 Webhook 地址",
            "notify test dingtalk",
            "测试消息已发送，请检查钉钉");
    }

    [RelayCommand]
    private void TestDiscord()
    {
        SendTestNotification(
            "Discord 测试",
            () => !string.IsNullOrEmpty(Settings.Notification.DiscordWebhookUrl.Trim()),
            "请先填写 Webhook 地址",
            "notify test discord",
            "测试消息已发送，请检查 Discord");
    }

    [RelayCommand]
    private void TestXxtui()
    {
        SendTestNotification(
            "xxtui 测试",
            () => !string.IsNullOrEmpty(Settings.Notification.XxtuiApiKey.Trim()),
            "请先填写 API Key",
            "notify test xxtui",
            "测试消息已发送");
    }

    [RelayCommand]
    private void TestOneBot()
    {
        SendTestNotification(
            "OneBot 测试",
            () => !string.IsNullOrEmpty(Settings.Notification.OneBotUrl.Trim()) &&
                  (!string.IsNullOrEmpty(Settings.Notification.OneBotUserId.Trim()) ||
                   !string.IsNullOrEmpty(Settings.Notification.OneBotGroupId.Trim())),
            "请填写 API 地址以及 QQ 号或群号（至少一个）",
            "notify test onebot",
            "测试消息已发送，请检查 QQ");
    }

    /// <summary>
    ///     发送测试通知的通用方法
    /// </summary>
    /// <param name="title">测试标题</param>
    /// <param name="validation">验证条件，返回 true 表示验证通过；对于需要提前发送命令的情况，可在此执行命令</param>
    /// <param name="errorMessage">验证失败时显示的错误消息</param>
    /// <param name="command">要发送到后端的命令（可选，为 null 或空时不发送）</param>
    /// <param name="successMessage">发送成功后显示的消息</param>
    private void SendTestNotification(string title, Func<bool> validation,
        string errorMessage, string command,
        string successMessage)
    {
        if (!validation())
        {
            _commonModel.ShowErrorToast(title, errorMessage);
            return;
        }
        
        var success = _backendService.SendInput(command);

        if (success)
            _commonModel.ShowSuccessToast(title, successMessage);
        else
            _commonModel.ShowErrorToast(title, errorMessage);
    }

    #endregion

    #region 快捷键监听修改逻辑

    private CustomizableKey? _currentListeningKey; // 正在监听的快捷键
    private bool _isChanged; // 是否已更改快捷键
    private string _tempKey = ""; // 临时存储原快捷键以防取消

    /// <summary>
    ///     开始监听指定的快捷键
    /// </summary>
    private void ListenKeyFor(CustomizableKey customizableKey)
    {
        if (TopLevelObject is null) return;
        if (_currentListeningKey is not null) ReleaseListening();
        _currentListeningKey = customizableKey;
        _isChanged = false;
        _tempKey = customizableKey.CurrentKey;
        customizableKey.CurrentKey = "按键盘设置快捷键";
        TopLevelObject.KeyUp += KeyUpHandler;
        TopLevelObject.PointerPressed += PointerPressedHandler;
    }

    /// <summary>
    ///     停止监听快捷键, 并根据是否更改决定是否保存新快捷键
    /// </summary>
    private void ReleaseListening()
    {
        if (TopLevelObject is null) return;
        if (!_isChanged && _currentListeningKey != null) _currentListeningKey.CurrentKey = _tempKey;
        TopLevelObject.KeyUp -= KeyUpHandler;
        TopLevelObject.PointerPressed -= PointerPressedHandler;
        _currentListeningKey = null;
    }

    private void PointerPressedHandler(object? sender, PointerPressedEventArgs e)
    {
        ReleaseListening();
    }

    private void KeyUpHandler(object? sender, KeyEventArgs e)
    {
        if (e.Key == Key.Escape)
        {
            ReleaseListening();
            return; // 退出方法，不执行后续修改逻辑
        }

        if (_currentListeningKey != null) _currentListeningKey.CurrentKey = e.Key.ToString();
        _isChanged = true;
        ReleaseListening();
    }

    #endregion

    #region 开发者模式多击版本号逻辑

    private int _versionClickCount;
    private DateTime _versionFirstClickTime;
    private const int VersionClickRequiredCount = 7;
    private static readonly TimeSpan VersionClickTimeWindow = TimeSpan.FromSeconds(3);

    [RelayCommand]
    private void OnVersionClicked()
    {
        var now = DateTime.UtcNow;

        if (_versionClickCount == 0 || now - _versionFirstClickTime > VersionClickTimeWindow)
        {
            _versionFirstClickTime = now;
            _versionClickCount = 1;
            return;
        }

        _versionClickCount++;

        if (_versionClickCount < VersionClickRequiredCount)
        {
            if (_versionClickCount > 3)
                _commonModel.ShowInfoToast("开发者模式",
                    Settings.Advanced.IsDeveloperModeEnabled
                        ? "您正处于开发者模式！"
                        : $"只需再执行 {VersionClickRequiredCount - _versionClickCount} 次操作，即可进入开发者模式");
            return;
        }

        _versionClickCount = 0;

        // 只负责开启开发者模式，关闭仍然通过显式开关
        if (!Settings.Advanced.IsDeveloperModeEnabled) Settings.Advanced.IsDeveloperModeEnabled = true;
        _commonModel.ShowInfoToast("开发者模式", "您正处于开发者模式！");
    }

    #endregion
}
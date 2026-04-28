using System;
using System.Threading.Tasks;
using System.ComponentModel;
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
    private readonly CacheService _cacheService;
    private readonly CommonModel _commonModel;
    private readonly AvaloniaList<CustomizableKey> _customizableKeys;
    private readonly RegistryService _registryService;
    private readonly IBackendService _backendService;

    private readonly SettingsService _settingsService;
    private readonly UpdateService _updateService;
    private readonly OverlayService _overlayService;

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
                IconText = "\uE1C6",
                DisplayText = Resources.MapText,
                DefaultKey = "M"
            }.Bind(() => Settings.General.HotkeyM,
                value => Settings.General.HotkeyM = value),
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
        {
            Settings.General.GamePaths.Add(gameInstallPath);
        }
        Settings.General.GamePathIndex = 0; // 切换到第一个路径
    }

    private void SetGameResolution()
    {
        if (!Settings.General.IsGameArgsEnabled) return;
        _registryService.SetTargetPcResolution();
    }

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

    #region 通知测试
    [RelayCommand]
    private async Task TestEmail()
    {
        await _commonModel.SendTestEmailAsync();
    }

    [RelayCommand]
    private void TestWebhook()
    {
        var endpoint = Settings.Notification.WebhookUrl.Trim();
        if (string.IsNullOrEmpty(endpoint))
        {
            _commonModel.ShowErrorToast("Webhook 测试", "请先填写 Webhook 地址");
            return;
        }
        _settingsService.Save();
        _ = _backendService.SendInput("notify test webhook");
        _commonModel.ShowInfoToast("Webhook 测试", $"测试请求已发送至：{endpoint}");
    }

    [RelayCommand]
    private void TestTelegram()
    {
        if (string.IsNullOrEmpty(Settings.Notification.TelegramBotToken.Trim()))
        {
            _commonModel.ShowErrorToast("Telegram 测试", "请先填写 Bot Token");
            return;
        }
        if (string.IsNullOrEmpty(Settings.Notification.TelegramChatId.Trim()))
        {
            _commonModel.ShowErrorToast("Telegram 测试", "请先填写 Chat ID");
            return;
        }
        _settingsService.Save();
        _ = _backendService.SendInput("notify test telegram");
        _commonModel.ShowInfoToast("Telegram 测试", "测试消息已发送，请检查 Telegram");
    }

    [RelayCommand]
    private void TestServerChan()
    {
        if (string.IsNullOrEmpty(Settings.Notification.ServerChanSendKey.Trim()))
        {
            _commonModel.ShowErrorToast("ServerChan 测试", "请先填写 SendKey");
            return;
        }
        _settingsService.Save();
        _ = _backendService.SendInput("notify test serverchan");
        _commonModel.ShowInfoToast("ServerChan 测试", "测试消息已发送，请检查微信");
    }

    [RelayCommand]
    private void TestBark()
    {
        if (string.IsNullOrEmpty(Settings.Notification.BarkDeviceKey.Trim()))
        {
            _commonModel.ShowErrorToast("Bark 测试", "请先填写设备 Key");
            return;
        }
        _settingsService.Save();
        _ = _backendService.SendInput("notify test bark");
        _commonModel.ShowInfoToast("Bark 测试", "测试消息已发送，请检查 iPhone");
    }

    [RelayCommand]
    private void TestFeishu()
    {
        if (string.IsNullOrEmpty(Settings.Notification.FeishuWebhookUrl.Trim()))
        {
            _commonModel.ShowErrorToast("飞书测试", "请先填写 Webhook 地址");
            return;
        }
        _settingsService.Save();
        _ = _backendService.SendInput("notify test feishu");
        _commonModel.ShowInfoToast("飞书测试", "测试消息已发送，请检查飞书");
    }

    [RelayCommand]
    private void TestWeCom()
    {
        if (string.IsNullOrEmpty(Settings.Notification.WeComWebhookUrl.Trim()))
        {
            _commonModel.ShowErrorToast("企业微信测试", "请先填写 Webhook 地址");
            return;
        }
        _settingsService.Save();
        _ = _backendService.SendInput("notify test wecom");
        _commonModel.ShowInfoToast("企业微信测试", "测试消息已发送，请检查企业微信");
    }

    [RelayCommand]
    private void TestDingTalk()
    {
        if (string.IsNullOrEmpty(Settings.Notification.DingTalkWebhookUrl.Trim()))
        {
            _commonModel.ShowErrorToast("钉钉测试", "请先填写 Webhook 地址");
            return;
        }
        _settingsService.Save();
        _ = _backendService.SendInput("notify test dingtalk");
        _commonModel.ShowInfoToast("钉钉测试", "测试消息已发送，请检查钉钉");
    }

    [RelayCommand]
    private void TestDiscord()
    {
        if (string.IsNullOrEmpty(Settings.Notification.DiscordWebhookUrl.Trim()))
        {
            _commonModel.ShowErrorToast("Discord 测试", "请先填写 Webhook 地址");
            return;
        }
        _settingsService.Save();
        _ = _backendService.SendInput("notify test discord");
        _commonModel.ShowInfoToast("Discord 测试", "测试消息已发送，请检查 Discord");
    }

    [RelayCommand]
    private void TestXxtui()
    {
        if (string.IsNullOrEmpty(Settings.Notification.XxtuiApiKey.Trim()))
        {
            _commonModel.ShowErrorToast("xxtui 测试", "请先填写 API Key");
            return;
        }
        _settingsService.Save();
        _ = _backendService.SendInput("notify test xxtui");
        _commonModel.ShowInfoToast("xxtui 测试", "测试消息已发送");
    }

    [RelayCommand]
    private void TestOneBot()
    {
        if (string.IsNullOrEmpty(Settings.Notification.OneBotUrl.Trim()))
        {
            _commonModel.ShowErrorToast("OneBot 测试", "请先填写 API 地址");
            return;
        }
        if (string.IsNullOrEmpty(Settings.Notification.OneBotUserId.Trim()) &&
            string.IsNullOrEmpty(Settings.Notification.OneBotGroupId.Trim()))
        {
            _commonModel.ShowErrorToast("OneBot 测试", "请填写 QQ 号或群号（至少一个）");
            return;
        }
        _settingsService.Save();
        _ = _backendService.SendInput("notify test onebot");
        _commonModel.ShowInfoToast("OneBot 测试", "测试消息已发送，请检查 QQ");
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
            if (_versionClickCount >3)
            {
                _commonModel.ShowInfoToast("开发者模式",
                    Settings.Advanced.IsDeveloperModeEnabled
                        ? "您正处于开发者模式！"
                        : $"只需再执行 {VersionClickRequiredCount - _versionClickCount} 次操作，即可进入开发者模式");
            }
            return;
        }

        _versionClickCount = 0;

        // 只负责开启开发者模式，关闭仍然通过显式开关
        if (!Settings.Advanced.IsDeveloperModeEnabled)
        {
            Settings.Advanced.IsDeveloperModeEnabled = true;
        }
        _commonModel.ShowInfoToast("开发者模式", "您正处于开发者模式！");
    }
    #endregion

    private void OnSettingsPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName is nameof(Settings.General.GameArgsWindowSize)
            or nameof(Settings.General.GameArgsFullScreenMode))
        {
            SetGameResolution();
        }
    }
}

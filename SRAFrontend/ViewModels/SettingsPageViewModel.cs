using System;
using System.Threading.Tasks;
using System.ComponentModel;
using System.Threading;
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
    private readonly ConfigService _configService;
    private CancellationTokenSource? _settingsSaveCts;

    /// <inheritdoc />
    public SettingsPageViewModel(
        SettingsService settingsService,
        UpdateService updateService,
        CacheService cacheService,
        CommonModel commonModel,
        RegistryService registryService,
        IBackendService backendService,
        OverlayService overlayService,
        ConfigService configService) : base(PageName.Setting,
        "\uE272")
    {
        _settingsService = settingsService;
        _updateService = updateService;
        _cacheService = cacheService;
        _registryService = registryService;
        _commonModel = commonModel;
        _backendService = backendService;
        _overlayService = overlayService;
        _configService = configService;
        // 任务通用设置中的 启动/停止 快捷键（非游戏内快捷键分组）
        StartStopKey = new CustomizableKey(ListenKeyFor)
        {
            IconText = "\uE3E4",
            DisplayText = Resources.StopHotkeyText,
            DefaultKey = "F9"
        }.Bind(() => settingsService.Settings.StartStopHotkey,
            value => settingsService.Settings.StartStopHotkey = value);

        _customizableKeys =
        [
            new CustomizableKey(ListenKeyFor)
            {
                IconText = "\uE1F6",
                DisplayText = Resources.ActivityText,
                DefaultKey = "F1"
            }.Bind(() => settingsService.Settings.ActivityHotkey,
                value => settingsService.Settings.ActivityHotkey = value),
            new CustomizableKey(ListenKeyFor)
            {
                IconText = "\uE320",
                DisplayText = Resources.ChronicleText,
                DefaultKey = "F2"
            }.Bind(() => settingsService.Settings.ChronicleHotkey,
                value => settingsService.Settings.ChronicleHotkey = value),
            new CustomizableKey(ListenKeyFor)
            {
                IconText = "\uE77E",
                DisplayText = Resources.WarpText,
                DefaultKey = "F3"
            }.Bind(() => settingsService.Settings.WarpHotkey,
                value => settingsService.Settings.WarpHotkey = value),
            new CustomizableKey(ListenKeyFor)
            {
                IconText = "\uE0E4",
                DisplayText = Resources.GuideText,
                DefaultKey = "F4"
            }.Bind(() => settingsService.Settings.GuideHotkey,
                value => settingsService.Settings.GuideHotkey = value),
            new CustomizableKey(ListenKeyFor)
            {
                IconText = "\uE1C6",
                DisplayText = Resources.MapText,
                DefaultKey = "M"
            }.Bind(() => settingsService.Settings.MapHotkey,
                value => settingsService.Settings.MapHotkey = value),
            new CustomizableKey(ListenKeyFor)
            {
                IconText = "\uE5E4",
                DisplayText = Resources.TechniqueText,
                DefaultKey = "E"
            }.Bind(() => settingsService.Settings.TechniqueHotkey,
                value => settingsService.Settings.TechniqueHotkey = value)
        ];

        DetectGamePath();
        SetGameResolution();
        if (IsOverlayEnabled) _overlayService.ShowOverlay();
        _overlayService.SetOverlayDebugInfoEnabled(Settings.IsOverlayDebugInfoEnabled);

        _settingsService.Settings.PropertyChanged += OnSettingsPropertyChanged;
        _settingsService.Settings.GamePaths.CollectionChanged += (_, _) => DebounceSaveSettings();
    }

    public IAvaloniaReadOnlyList<CustomizableKey> CustomizableKeys => _customizableKeys;
    public CustomizableKey StartStopKey { get; }

    public Settings Settings => _settingsService.Settings;
    public Cache Cache => _cacheService.Cache;
    public string VersionText => Settings.Version;

    public string MirrorChyanCdk
    {
        get => Settings.MirrorChyanCdk;
        set
        {
            // 先更新存储的值（即使后续验证失败，也保留用户输入便于修改）
            Settings.MirrorChyanCdk = value;
            OnPropertyChanged(); // 通知UI属性已变更
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
            "appdata" => PathString.AppDataSraDir,
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
        Settings.GamePaths.Add(localPath);
        Settings.GamePathIndex = Settings.GamePaths.Count - 1; // 切换到新添加的路径
    }

    [RelayCommand]
    private void DetectGamePath()
    {
        if (!Settings.IsAutoDetectGamePath) return;
        Settings.GamePaths.Clear();
        Settings.GamePaths.AddRange(_registryService.GetGameInstallPaths());
        Settings.GamePathIndex = 0; // 切换到第一个路径
    }

    private void SetGameResolution()
    {
        if (!Settings.LaunchArgumentsEnabled) return;
        _registryService.SetTargetPcResolution();
    }

    public Config? CurrentConfig => _configService.Config;

    public bool IsOverlayEnabled
    {
        get => Settings.IsOverlayEnabled;
        set
        {
            Settings.IsOverlayEnabled = value;
            if (value)
                _overlayService.ShowOverlay();
            else
                _overlayService.CloseOverlay();
        }
    }
    
    public bool IsOverlayDebugInfoEnabled
    {
        get => Settings.IsOverlayDebugInfoEnabled;
        set
        {
            Settings.IsOverlayDebugInfoEnabled = value;
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
        var endpoint = Settings.WebhookEndpoint.Trim();
        if (string.IsNullOrEmpty(endpoint))
        {
            _commonModel.ShowErrorToast("Webhook 测试", "请先填写 Webhook 地址");
            return;
        }
        _settingsService.SaveSettings();
        _ = _backendService.SendInput("notify test webhook");
        _commonModel.ShowInfoToast("Webhook 测试", $"测试请求已发送至：{endpoint}");
    }

    [RelayCommand]
    private void TestTelegram()
    {
        if (string.IsNullOrEmpty(Settings.TelegramBotToken.Trim()))
        {
            _commonModel.ShowErrorToast("Telegram 测试", "请先填写 Bot Token");
            return;
        }
        if (string.IsNullOrEmpty(Settings.TelegramChatId.Trim()))
        {
            _commonModel.ShowErrorToast("Telegram 测试", "请先填写 Chat ID");
            return;
        }
        _settingsService.SaveSettings();
        _ = _backendService.SendInput("notify test telegram");
        _commonModel.ShowInfoToast("Telegram 测试", "测试消息已发送，请检查 Telegram");
    }

    [RelayCommand]
    private void TestServerChan()
    {
        if (string.IsNullOrEmpty(Settings.ServerChanSendKey.Trim()))
        {
            _commonModel.ShowErrorToast("ServerChan 测试", "请先填写 SendKey");
            return;
        }
        _settingsService.SaveSettings();
        _ = _backendService.SendInput("notify test serverchan");
        _commonModel.ShowInfoToast("ServerChan 测试", "测试消息已发送，请检查微信");
    }

    [RelayCommand]
    private void TestBark()
    {
        if (string.IsNullOrEmpty(Settings.BarkDeviceKey.Trim()))
        {
            _commonModel.ShowErrorToast("Bark 测试", "请先填写设备 Key");
            return;
        }
        _settingsService.SaveSettings();
        _ = _backendService.SendInput("notify test bark");
        _commonModel.ShowInfoToast("Bark 测试", "测试消息已发送，请检查 iPhone");
    }

    [RelayCommand]
    private void TestFeishu()
    {
        if (string.IsNullOrEmpty(Settings.FeishuWebhookUrl.Trim()))
        {
            _commonModel.ShowErrorToast("飞书测试", "请先填写 Webhook 地址");
            return;
        }
        _settingsService.SaveSettings();
        _ = _backendService.SendInput("notify test feishu");
        _commonModel.ShowInfoToast("飞书测试", "测试消息已发送，请检查飞书");
    }

    [RelayCommand]
    private void TestWeCom()
    {
        if (string.IsNullOrEmpty(Settings.WeComWebhookUrl.Trim()))
        {
            _commonModel.ShowErrorToast("企业微信测试", "请先填写 Webhook 地址");
            return;
        }
        _settingsService.SaveSettings();
        _ = _backendService.SendInput("notify test wecom");
        _commonModel.ShowInfoToast("企业微信测试", "测试消息已发送，请检查企业微信");
    }

    [RelayCommand]
    private void TestDingTalk()
    {
        if (string.IsNullOrEmpty(Settings.DingTalkWebhookUrl.Trim()))
        {
            _commonModel.ShowErrorToast("钉钉测试", "请先填写 Webhook 地址");
            return;
        }
        _settingsService.SaveSettings();
        _ = _backendService.SendInput("notify test dingtalk");
        _commonModel.ShowInfoToast("钉钉测试", "测试消息已发送，请检查钉钉");
    }

    [RelayCommand]
    private void TestDiscord()
    {
        if (string.IsNullOrEmpty(Settings.DiscordWebhookUrl.Trim()))
        {
            _commonModel.ShowErrorToast("Discord 测试", "请先填写 Webhook 地址");
            return;
        }
        _settingsService.SaveSettings();
        _ = _backendService.SendInput("notify test discord");
        _commonModel.ShowInfoToast("Discord 测试", "测试消息已发送，请检查 Discord");
    }

    [RelayCommand]
    private void TestXxtui()
    {
        if (string.IsNullOrEmpty(Settings.XxtuiApiKey.Trim()))
        {
            _commonModel.ShowErrorToast("xxtui 测试", "请先填写 API Key");
            return;
        }
        _settingsService.SaveSettings();
        _ = _backendService.SendInput("notify test xxtui");
        _commonModel.ShowInfoToast("xxtui 测试", "测试消息已发送");
    }

    [RelayCommand]
    private void TestOneBot()
    {
        if (string.IsNullOrEmpty(Settings.OneBotEndpoint.Trim()))
        {
            _commonModel.ShowErrorToast("OneBot 测试", "请先填写 API 地址");
            return;
        }
        if (string.IsNullOrEmpty(Settings.OneBotUserId.Trim()) &&
            string.IsNullOrEmpty(Settings.OneBotGroupId.Trim()))
        {
            _commonModel.ShowErrorToast("OneBot 测试", "请填写 QQ 号或群号（至少一个）");
            return;
        }
        _settingsService.SaveSettings();
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
                    Settings.IsDeveloperMode
                        ? "您正处于开发者模式！"
                        : $"只需再执行 {VersionClickRequiredCount - _versionClickCount} 次操作，即可进入开发者模式");
            }
            return;
        }

        _versionClickCount = 0;

        // 只负责开启开发者模式，关闭仍然通过显式开关
        if (!_settingsService.Settings.IsDeveloperMode)
        {
            _settingsService.Settings.IsDeveloperMode = true;
            _settingsService.SaveSettings();
        }
        _commonModel.ShowInfoToast("开发者模式", "您正处于开发者模式！");
    }
    #endregion

    private void OnSettingsPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName is nameof(Settings.LaunchArgumentsScreenSize)
            or nameof(Settings.LaunchArgumentsFullScreenMode))
        {
            SetGameResolution();
        }

        DebounceSaveSettings();
    }

    private void DebounceSaveSettings()
    {
        _settingsSaveCts?.Cancel();
        _settingsSaveCts?.Dispose();
        _settingsSaveCts = new CancellationTokenSource();
        _ = SaveSettingsAsync(_settingsSaveCts.Token);
    }

    private async Task SaveSettingsAsync(CancellationToken cancellationToken)
    {
        try
        {
            await Task.Delay(500, cancellationToken);
            _settingsService.SaveSettings();
        }
        catch (TaskCanceledException)
        {
        }
    }
}

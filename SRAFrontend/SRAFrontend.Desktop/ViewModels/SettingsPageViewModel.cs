using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Avalonia.Collections;
using Avalonia.Controls;
using Avalonia.Media;
using Avalonia.Platform.Storage;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Data;
using SRAFrontend.Desktop.Services;
using SRAFrontend.Desktop.Views;
using SRAFrontend.Localization;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SRAFrontend.Utils;
using SukiUI.Controls;
using SukiUI.MessageBox;
using CustomizableKey = SRAFrontend.Desktop.Models.CustomizableKey;

namespace SRAFrontend.Desktop.ViewModels;

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
    private readonly ReportService _reportService;
    /// <inheritdoc />
    public SettingsPageViewModel(
        SettingsService settingsService,
        UpdateService updateService,
        CacheService cacheService,
        CommonModel commonModel,
        RegistryService registryService,
        IBackendService backendService,
        OverlayService overlayService, ReportService reportService) : base(PageName.Setting,
        "\uE272")
    {
        _settingsService = settingsService;
        _updateService = updateService;
        _cacheService = cacheService;
        _registryService = registryService;
        _commonModel = commonModel;
        _backendService = backendService;
        _overlayService = overlayService;
        _reportService = reportService;
        // 任务通用设置中的 启动/停止 快捷键（非游戏内快捷键分组）
        StartStopKey = new CustomizableKey
        {
            IconText = "\uE3E4",
            DisplayText = Resources.StopHotkeyText,
            DefaultKey = "F9"
        }.Configure(() => Settings.General.HotkeyStop,
            value => Settings.General.HotkeyStop = value);

        _customizableKeys =
        [
            new CustomizableKey
            {
                IconText = "\uE1F6",
                DisplayText = Resources.ActivityText,
                DefaultKey = "F1"
            }.Configure(() => Settings.General.HotkeyF1,
                value => Settings.General.HotkeyF1 = value),
            new CustomizableKey
            {
                IconText = "\uE320",
                DisplayText = Resources.ChronicleText,
                DefaultKey = "F2"
            }.Configure(() => Settings.General.HotkeyF2,
                value => Settings.General.HotkeyF2 = value),
            new CustomizableKey
            {
                IconText = "\uE77E",
                DisplayText = Resources.WarpText,
                DefaultKey = "F3"
            }.Configure(() => Settings.General.HotkeyF3,
                value => Settings.General.HotkeyF3 = value),
            new CustomizableKey
            {
                IconText = "\uE0E4",
                DisplayText = Resources.GuideText,
                DefaultKey = "F4"
            }.Configure(() => Settings.General.HotkeyF4,
                value => Settings.General.HotkeyF4 = value),
            new CustomizableKey
            {
                IconText = "\uE5E4",
                DisplayText = Resources.TechniqueText,
                DefaultKey = "E"
            }.Configure(() => Settings.General.HotkeyE,
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

    // 显示模式在配置里以中文值保存，展示文案按界面语言取资源。
    private static readonly string[] FullScreenModeValues = ["窗口化", "全屏幕"];

    public string[] FullScreenModeNames => [Resources.WindowedModeText, Resources.FullscreenModeText];

    public int FullScreenModeIndex
    {
        get => Math.Max(0, Array.IndexOf(FullScreenModeValues, Settings.General.GameArgsFullScreenMode));
        set
        {
            if (value >= 0 && value < FullScreenModeValues.Length)
                Settings.General.GameArgsFullScreenMode = FullScreenModeValues[value];
            OnPropertyChanged();
        }
    }

    public DisplaySettings DisplaySettings => Settings.Display;
    public NotificationSettings NotificationSettings => Settings.Notification;
    public UpdateSettings UpdateSettings => Settings.Update;
    public AdvancedSettings AdvancedSettings => Settings.Advanced;
    public Cache Cache => _cacheService.Cache;
    public static string VersionText => AppSettings.Version;
    public string DeviceId => _reportService.GetDeviceId();
    /// <summary>ComboBox 绑定用：对外仍是 0/1/2 的索引。</summary>
    public int LanguageIndex
    {
        get => (int)DisplaySettings.Language;
        set => DisplaySettings.Language = (UiLanguage)value;
    }

    public bool IsLanguageNotChinese => DisplaySettings.Language != UiLanguage.Chinese;

    public string GameChineseLanguageTip =>
        Resources.ResourceManager.GetString(nameof(GameChineseLanguageTip), Resources.Culture) ?? "";

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
                Cache.CdkStatus = Resources.CdkLengthError;
                Cache.CdkStatusForeground = "#F5222D";
                return;
            }

            // 长度正确时，触发异步验证（不阻塞setter）
            _ = VerifyCdkAsync(); // 使用_忽略未等待的Task（需确保异常处理）
        }
    }

    public TopLevel? TopLevelObject
    {
        get;
        set
        {
            field = value;
            if (value is not null) InitializeKeyBindings(value);
        }
    }

    private void InitializeKeyBindings(TopLevel topLevel)
    {
        StartStopKey.AttachTopLevel(topLevel);
        foreach (var key in _customizableKeys)
            key.AttachTopLevel(topLevel);
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

    [RelayCommand]
    private async Task VerifyCdkAsync()
    {
        var cdk = MirrorChyanCdk;
        // 显示"验证中"状态
        Cache.CdkStatus = Resources.VerifyingMessage;
        Cache.CdkStatusForeground = "#FAAD14"; // 黄色表示处理中

        // 执行异步验证
        var response = await _updateService.VerifyCdkAsync(cdk);

        if (response is null)
        {
            Cache.CdkStatus = Resources.VerificationServiceError;
            Cache.CdkStatusForeground = "#F5222D"; // 红色表示错误
            return;
        }

        if (response.Code == 0)
        {
            var leastTime = DateTimeOffset.FromUnixTimeSeconds(response.Data.CdkExpiredTime);
            Cache.CdkStatus = string.Format(Resources.Culture, Resources.CdkValidUntilFormat, leastTime);
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

    /// <summary>重新安装最新版本流程是否进行中（用于禁用按钮，防止重复触发）</summary>
    [ObservableProperty]
    private bool _isReinstalling;

    [RelayCommand]
    private async Task ReinstallLatest()
    {
        if (IsReinstalling) return;
        IsReinstalling = true;
        try
        {
            await _commonModel.ReinstallLatestAsync();
        }
        finally
        {
            IsReinstalling = false;
        }
    }

    /// <summary>资源完整性检查是否进行中（用于禁用按钮，防止重复触发）</summary>
    [ObservableProperty]
    private bool _isResourceChecking;

    /// <summary>根据安装包内置的 MD5 清单（manifest.md5.json）校验应用文件完整性</summary>
    [RelayCommand]
    private async Task CheckResourceIntegrityAsync()
    {
        if (IsResourceChecking) return;
        IsResourceChecking = true;
        try
        {
            var result = await Task.Run(() => ZipUtil.CheckIntegrity(DataPath.AppRoot));
            if (result.IsIntact)
            {
                _commonModel.ShowSuccessToast(Resources.ResourceIntegrityCheckText,
                    string.Format(Resources.Culture, Resources.IntegrityCheckPassedMessage, result.TotalCount));
                return;
            }

            var problems = new StackPanel { Spacing = 8 };
            AddProblemFiles(problems, Resources.MissingFilesMessage, result.MissingFiles);
            AddProblemFiles(problems, Resources.CorruptedFilesMessage, result.CorruptedFiles);
            await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
            {
                Header = Resources.ResourceIntegrityCheckText,
                Content = new ScrollViewer { MaxHeight = 400, Content = problems },
                ActionButtonsSource =
                    [SukiMessageBoxButtonsFactory.CreateButton(Resources.GotItText, SukiMessageBoxResult.Cancel)]
            });
        }
        catch (FileNotFoundException)
        {
            _commonModel.ShowErrorToast(Resources.ResourceIntegrityCheckText,
                Resources.IntegrityManifestMissingMessage);
        }
        catch (Exception e)
        {
            _commonModel.ShowErrorToast(Resources.ResourceIntegrityCheckText, string.Format(Resources.Culture, Resources.CheckFailedError, e.Message));
        }
        finally
        {
            IsResourceChecking = false;
        }
    }

    /// <summary>把一组问题文件以标题 + 明细列表的形式追加到对话框面板（最多展示 50 条，超出部分汇总）</summary>
    private static void AddProblemFiles(StackPanel panel, string header, IReadOnlyList<string> files)
    {
        if (files.Count == 0) return;
        panel.Children.Add(new TextBlock
        {
            Text = string.Format(Resources.Culture, Resources.FileCountFormat, header, files.Count),
            FontWeight = FontWeight.Bold
        });
        foreach (var file in files.Take(50))
            panel.Children.Add(new TextBlock { Text = file, FontSize = 12, Opacity = 0.72 });
        if (files.Count > 50)
            panel.Children.Add(new TextBlock
            {
                Text = string.Format(Resources.Culture, Resources.OmittedFilesFormat, files.Count - 50),
                FontSize = 12,
                Opacity = 0.72
            });
    }

    /// <summary>资源清理流程是否进行中（用于禁用按钮，防止重复触发）</summary>
    [ObservableProperty]
    private bool _isResourceCleaning;

    /// <summary>扫描应用目录下不在 MD5 清单中的冗余文件，弹窗勾选后删除</summary>
    [RelayCommand]
    private async Task CleanupResourcesAsync()
    {
        if (IsResourceCleaning) return;
        IsResourceCleaning = true;
        try
        {
            var redundant = await Task.Run(() => ZipUtil.ScanRedundantFiles(DataPath.AppRoot));
            if (redundant.Count == 0)
            {
                _commonModel.ShowSuccessToast(Resources.ResourceCleanupText, Resources.NoFilesToCleanMessage);
                return;
            }

            var viewModel = new ResourceCleanupViewModel(DataPath.AppRoot, redundant);
            var view = new ResourceCleanupView { DataContext = viewModel };
            var result = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
            {
                Header = Resources.ResourceCleanupText,
                Content = view,
                ActionButtonsSource =
                [
                    SukiMessageBoxButtonsFactory.CreateButton(Resources.DeleteSelectedText, SukiMessageBoxResult.Yes, "Flat"),
                    SukiMessageBoxButtonsFactory.CreateButton(Resources.CancelText, SukiMessageBoxResult.Cancel)
                ]
            });
            if (result is not SukiMessageBoxResult.Yes) return;

            var (deletedCount, freedBytes, failed) = await viewModel.DeleteSelectedAsync();
            if (failed.Count == 0)
                _commonModel.ShowSuccessToast(Resources.ResourceCleanupText,
                    string.Format(Resources.Culture, Resources.FilesDeletedFormat, deletedCount, ZipUtil.FormatFileSize(freedBytes)));
            else
                _commonModel.ShowErrorToast(Resources.ResourceCleanupText,
                    string.Format(Resources.Culture, Resources.FilesDeletedWithFailuresMessage, deletedCount, failed.Count,
                        string.Join(Resources.ListSeparatorText, failed.Take(3)),
                        failed.Count > 3 ? Resources.MoreFilesSuffix : ""));
        }
        catch (FileNotFoundException)
        {
            _commonModel.ShowErrorToast(Resources.ResourceCleanupText,
                Resources.RedundantManifestMissingMessage);
        }
        catch (Exception e)
        {
            _commonModel.ShowErrorToast(Resources.ResourceCleanupText, string.Format(Resources.Culture, Resources.ScanFailedError, e.Message));
        }
        finally
        {
            IsResourceCleaning = false;
        }
    }

    /// <summary>当前生效的下载保存目录（配置为空白时回退到默认临时目录）</summary>
    public string EffectiveDownloadPath =>
        string.IsNullOrWhiteSpace(UpdateSettings.DownloadPath)
            ? DataPath.TempDir
            : UpdateSettings.DownloadPath;

    /// <summary>下载目录输入框的占位提示（展示默认目录）</summary>
    public string DownloadPathWatermark => DataPath.TempDir;

    /// <summary>通过系统文件夹选择器更改下载文件的保存目录</summary>
    [RelayCommand]
    private async Task ChangeDownloadPath()
    {
        if (TopLevelObject is null) return;
        var folders = await TopLevelObject.StorageProvider.OpenFolderPickerAsync(new FolderPickerOpenOptions
        {
            Title = Resources.DownloadFolderPickerTitle,
            AllowMultiple = false
        });
        if (folders.Count == 0) return;

        var path = folders[0].Path.LocalPath;
        try
        {
            Directory.CreateDirectory(path);
        }
        catch (Exception)
        {
            await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
            {
                Header = Resources.FolderUnavailableMessage,
                Content = string.Format(Resources.Culture, Resources.FolderAccessErrorMessage, path),
                ActionButtonsSource = [SukiMessageBoxButtonsFactory.CreateButton(Resources.GotItText, SukiMessageBoxResult.Cancel)]
            });
            return;
        }

        UpdateSettings.DownloadPath = path;
        OnPropertyChanged(nameof(EffectiveDownloadPath));
    }

    /// <summary>在系统文件管理器中打开当前下载目录</summary>
    [RelayCommand]
    private void OpenDownloadPath()
    {
        var path = EffectiveDownloadPath;
        try
        {
            Directory.CreateDirectory(path);
        }
        catch (Exception)
        {
            // 创建失败时交由 OpenFolderInExplorer 的不存在目录分支提示用户
        }

        _commonModel.OpenFolderInExplorer(path);
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
            "backendLogs" => DataPath.BackendLogsDir,
            "frontendLogs" => DataPath.FrontendLogsDir,
            "configs" => DataPath.ConfigsDir,
            "appdata" => DataPath.AppDataDir,
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

        if (e.PropertyName == nameof(UpdateSettings.DownloadPath))
            OnPropertyChanged(nameof(EffectiveDownloadPath));

        if (e.PropertyName == nameof(DisplaySettings.Language))
            OnLanguageChanged();
    }

    private void OnLanguageChanged()
    {
        _settingsService.Save();
        OnPropertyChanged(nameof(IsLanguageNotChinese));
        OnPropertyChanged(nameof(LanguageIndex));
        OnPropertyChanged(nameof(GameChineseLanguageTip));
        _ = AskRestartAsync();
    }

    private async Task AskRestartAsync()
    {
        var isChinese = DisplaySettings.Language != UiLanguage.English;
        var restartButton = SukiMessageBoxButtonsFactory.CreateButton(
            isChinese ? Resources.RestartNowText : "Restart Now", SukiMessageBoxResult.Yes, "Flat");
        var laterButton = SukiMessageBoxButtonsFactory.CreateButton(
            isChinese ? Resources.LaterText : "Later", SukiMessageBoxResult.Cancel);

        var result = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = isChinese ? Resources.LanguageChangedMessage : "Language Changed",
            Content = isChinese
                ? Resources.LanguageRestartConfirmMessage
                : "The application needs to restart to apply the new language. Restart now?",
            ActionButtonsSource = [restartButton, laterButton]
        });

        if (result is SukiMessageBoxResult.Yes)
            RestartApplication();
    }

    private void RestartApplication()
    {
        var exePath = DataPath.SraExecutablePath;
        try
        {
            _settingsService.Save();
            Process.Start(new ProcessStartInfo
            {
                FileName = exePath,
                WorkingDirectory = Environment.CurrentDirectory,
                UseShellExecute = true
            });
            Environment.Exit(0);
        }
        catch (Exception e)
        {
            var isChinese = DisplaySettings.Language != UiLanguage.English;
            _commonModel.ShowErrorToast(
                isChinese ? Resources.RestartFailedError : "Restart Failed",
                string.Format(Resources.Culture, Resources.LabelValueFormat, (isChinese ? "发生错误" : "An error occurred"), e.Message));
        }
    }

    [RelayCommand]
    private async Task TestEmailAsync()
    {
        await SendTestNotificationAsync(
            Resources.EmailTestText,
            () => !string.IsNullOrEmpty(Settings.Notification.SmtpServer.Trim()) &&
                  Settings.Notification.SmtpPort > 0 &&
                  !string.IsNullOrEmpty(Settings.Notification.SmtpSender.Trim()) &&
                  !string.IsNullOrEmpty(Settings.Notification.SmtpAuthCode.Trim()) &&
                  !string.IsNullOrEmpty(Settings.Notification.SmtpReceiver.Trim()),
            Resources.SmtpSetupRequiredMessage,
            "notify test email",
            Resources.EmailTestSentMessage);
    }

    [RelayCommand]
    private async Task TestWebhookAsync()
    {
        await SendTestNotificationAsync(
            Resources.WebhookTestText,
            () => !string.IsNullOrEmpty(Settings.Notification.WebhookUrl.Trim()),
            Resources.WebhookUrlRequiredMessage,
            "notify test webhook",
            string.Format(Resources.Culture, Resources.WebhookTestSentMessage, Settings.Notification.WebhookUrl.Trim()));
    }

    [RelayCommand]
    private async Task TestTelegramAsync()
    {
        await SendTestNotificationAsync(
            Resources.TelegramTestText,
            () => !string.IsNullOrEmpty(Settings.Notification.TelegramBotToken.Trim()) &&
                  !string.IsNullOrEmpty(Settings.Notification.TelegramChatId.Trim()),
            Resources.TelegramCredentialsRequiredMessage,
            "notify test telegram",
            Resources.TelegramTestSentMessage);
    }

    [RelayCommand]
    private async Task TestServerChanAsync()
    {
        await SendTestNotificationAsync(
            Resources.ServerChanTestText,
            () => !string.IsNullOrEmpty(Settings.Notification.ServerChanSendKey.Trim()),
            Resources.SendKeyRequiredMessage,
            "notify test serverchan",
            Resources.ServerChanTestSentMessage);
    }

    [RelayCommand]
    private async Task TestBarkAsync()
    {
        await SendTestNotificationAsync(
            Resources.BarkTestText,
            () => !string.IsNullOrEmpty(Settings.Notification.BarkDeviceKey.Trim()),
            Resources.BarkDeviceKeyRequiredMessage,
            "notify test bark",
            Resources.BarkTestSentMessage);
    }

    [RelayCommand]
    private async Task TestFeishuAsync()
    {
        await SendTestNotificationAsync(
            Resources.FeishuTestText,
            () => !string.IsNullOrEmpty(Settings.Notification.FeishuWebhookUrl.Trim()),
            Resources.WebhookUrlRequiredMessage,
            "notify test feishu",
            Resources.FeishuTestSentMessage);
    }

    [RelayCommand]
    private async Task TestWeComAsync()
    {
        await SendTestNotificationAsync(
            Resources.WeComTestText,
            () => !string.IsNullOrEmpty(Settings.Notification.WeComWebhookUrl.Trim()),
            Resources.WebhookUrlRequiredMessage,
            "notify test wecom",
            Resources.WeComTestSentMessage);
    }

    [RelayCommand]
    private async Task TestDingTalkAsync()
    {
        await SendTestNotificationAsync(
            Resources.DingTalkTestText,
            () => !string.IsNullOrEmpty(Settings.Notification.DingTalkWebhookUrl.Trim()),
            Resources.WebhookUrlRequiredMessage,
            "notify test dingtalk",
            Resources.DingTalkTestSentMessage);
    }

    [RelayCommand]
    private async Task TestDiscordAsync()
    {
        await SendTestNotificationAsync(
            Resources.DiscordTestText,
            () => !string.IsNullOrEmpty(Settings.Notification.DiscordWebhookUrl.Trim()),
            Resources.WebhookUrlRequiredMessage,
            "notify test discord",
            Resources.DiscordTestSentMessage);
    }

    [RelayCommand]
    private async Task TestXxtuiAsync()
    {
        await SendTestNotificationAsync(
            Resources.XxtuiTestText,
            () => !string.IsNullOrEmpty(Settings.Notification.XxtuiApiKey.Trim()),
            Resources.XxtuiApiKeyRequiredMessage,
            "notify test xxtui",
            Resources.TestMessageSentMessage);
    }

    [RelayCommand]
    private async Task TestOneBotAsync()
    {
        await SendTestNotificationAsync(
            Resources.OneBotTestText,
            () => !string.IsNullOrEmpty(Settings.Notification.OneBotUrl.Trim()) &&
                  (!string.IsNullOrEmpty(Settings.Notification.OneBotUserId.Trim()) ||
                   !string.IsNullOrEmpty(Settings.Notification.OneBotGroupId.Trim())),
            Resources.OneBotTargetRequiredMessage,
            "notify test onebot",
            Resources.OneBotTestSentMessage);
    }

    /// <summary>
    ///     发送测试通知的通用方法
    /// </summary>
    /// <param name="title">测试标题</param>
    /// <param name="validation">验证条件，返回 true 表示验证通过；对于需要提前发送命令的情况，可在此执行命令</param>
    /// <param name="errorMessage">验证失败时显示的错误消息</param>
    /// <param name="command">要发送到后端的命令（可选，为 null 或空时不发送）</param>
    /// <param name="successMessage">发送成功后显示的消息</param>
    private async Task SendTestNotificationAsync(string title, Func<bool> validation,
        string errorMessage, string command,
        string successMessage)
    {
        if (!validation())
        {
            _commonModel.ShowErrorToast(title, errorMessage);
            return;
        }
        
        var success = await _backendService.SendInputAsync(command);

        if (success)
            _commonModel.ShowSuccessToast(title, successMessage);
        else
            _commonModel.ShowErrorToast(title, errorMessage);
    }

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
                _commonModel.ShowInfoToast(Resources.DeveloperModeText, Settings.Advanced.IsDeveloperModeEnabled ? Resources.DeveloperModeActiveMessage : string.Format(Resources.Culture, Resources.DeveloperModeCountdownFormat, VersionClickRequiredCount - _versionClickCount));
            return;
        }

        _versionClickCount = 0;

        // 只负责开启开发者模式，关闭仍然通过显式开关
        if (!Settings.Advanced.IsDeveloperModeEnabled) Settings.Advanced.IsDeveloperModeEnabled = true;
        _commonModel.ShowInfoToast(Resources.DeveloperModeText, Resources.DeveloperModeActiveMessage);
    }

    #endregion
}


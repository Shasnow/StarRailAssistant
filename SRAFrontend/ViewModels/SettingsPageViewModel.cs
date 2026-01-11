using System;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using Avalonia.Collections;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Platform.Storage;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Win32;
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

    private readonly SettingsService _settingsService;
    private readonly UpdateService _updateService;

    /// <inheritdoc />
    public SettingsPageViewModel(SettingsService settingsService,
        UpdateService updateService,
        CacheService cacheService,
        CommonModel commonModel) : base(PageName.Setting,
        "\uE272")
    {
        _settingsService = settingsService;
        _updateService = updateService;
        _cacheService = cacheService;
        _commonModel = commonModel;
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
            _ = VerifyCdkAsync(value); // 使用_忽略未等待的Task（需确保异常处理）
        }
    }

    public TopLevel? TopLevelObject { get; set; }

    private async Task VerifyCdkAsync(string cdk)
    {
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
            Cache.CdkStatus = "有效的CDK" + $" 到期时间: {leastTime:yyyy-MM-dd HH:mm:ss}";
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
        Settings.GamePath = files[0].Path.LocalPath;
    }
    
    [RelayCommand]
    private void DetectGamePath()
    {
        if (!Settings.IsAutoDetectGamePath) return;
        Settings.GamePath = "无法自动检测游戏路径";
        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows)) return;
        var userKey = Registry.CurrentUser;
        using var hkrpgcnKey =
            userKey.OpenSubKey(@"Software\miHoYo\HYP\standalone\14_0\hkrpg_cn\6P5gHMNyK3\hkrpg_cn")
            ?? userKey.OpenSubKey(@"Software\miHoYo\HYP\1_1\hkrpg_cn");
        if (hkrpgcnKey is null) return;
        var gameInstallPath = hkrpgcnKey.GetValue("GameInstallPath") as string;
        if (string.IsNullOrEmpty(gameInstallPath)) return;
        Settings.GamePath = $"{gameInstallPath.Replace('\\','/')}/StarRail.exe";
    }
    
    #region 快捷键监听修改逻辑

    private CustomizableKey? _currentListeningKey; // 正在监听的快捷键
    private bool _isChanged; // 是否已更改快捷键
    private string _tempKey = ""; // 临时存储原快捷键以防取消

    /// <summary>
    /// 开始监听指定的快捷键
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
    /// 停止监听快捷键, 并根据是否更改决定是否保存新快捷键
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
}
using System.Text.Json.Serialization;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

public partial class Settings : ObservableObject
{
    /// <summary>
    ///     是否启用线程安全模式 已过时，现在使用进程而非线程来防止阻塞
    /// </summary>
    [ObservableProperty]private bool _threadSafety = false;

    [ObservableProperty] private double _backgroundOpacity  = 0.9;
    [ObservableProperty] private int _language  = 1; // 0: English, 1: Simplified Chinese
    [ObservableProperty] private double _zoom  = 1; // 屏幕缩放比例
    [ObservableProperty] private double _confidenceThreshold  = 0.9; // 识图置信度阈值
    [ObservableProperty] private int _downloadChannel  = 1; // 0: Mirror, 1: GitHub
    [ObservableProperty] private int _appChannel;  // 0: stable, 1: beta
    [ObservableProperty] private string _mirrorChyanCdk = "";
    [ObservableProperty] private bool _enableAutoUpdate = true; // 是否启用自动更新
    [ObservableProperty] private AvaloniaList<string> _proxies = ["https://tvv.tw/"]; // 代理列表
    [ObservableProperty] private int _defaultPage = 0; // 启动时默认页面索引
    [JsonIgnore] public static string Version => "2.0.0"; // 应用版本号
    [ObservableProperty] private bool _allowNotifications = true; // 是否允许通知
    [ObservableProperty] private bool _allowSystemNotifications = true; // 是否允许系统通知
    [ObservableProperty] private bool _allowEmailNotifications = false; // 是否允许邮件通知
    [ObservableProperty] private bool _enableStartupLaunch = false; // 是否启用开机自启动
    [ObservableProperty] private bool _enableMinimizeToTray = false; // 是否启用最小化到托盘
}
using System;
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

    [ObservableProperty] private double _backgroundOpacity = 0.9; // 背景图不透明度
    [ObservableProperty] private double _ctrlPanelOpacity = 0.9; // 控制面板不透明度
    [ObservableProperty] private string _backgroundImagePath = ""; // 背景图路径
    [ObservableProperty] private double _confidenceThreshold = 0.9; // 识图置信度阈值
    [ObservableProperty] private int _defaultPage; // 启动时默认页面索引
    [ObservableProperty] private int _downloadChannel = 1; // 0: Mirror, 1: GitHub
    [ObservableProperty] private string _emailAuthCode = ""; // 邮件授权码
    [ObservableProperty] private string _emailReceiver = ""; // 接收邮件地址
    [ObservableProperty] private string _emailSender = ""; // 发送邮件地址
    [ObservableProperty] private bool _enableAutoUpdate = true; // 是否启用自动更新
    [ObservableProperty] private bool _enableMinimizeToTray; // 是否启用最小化到托盘
    [ObservableProperty] private bool _enableStartupLaunch; // 是否启用开机自启动
    [ObservableProperty] private int _language = 1; // 0: English, 1: Simplified Chinese

    [ObservableProperty] [property: JsonIgnore]
    private string _mirrorChyanCdk = "";

    [ObservableProperty] private AvaloniaList<string> _proxies =
    [
        "https://tvv.tw/",
        "https://github.moeyy.xyz/",
        "https://ghproxy.1888866.xyz/",
        "https://github.chenc.dev/"
    ]; // 代理列表

    [ObservableProperty] private int _smtpPort = 465; // SMTP服务器端口

    [ObservableProperty] private string _smtpServer = "smtp.qq.com"; // SMTP服务器地址

    /// <summary>
    ///     是否启用线程安全模式 已过时，现在使用进程而非线程来防止阻塞
    /// </summary>
    [ObservableProperty] private bool _threadSafety;

    [ObservableProperty] private double _zoom = 1; // 屏幕缩放比例
    [JsonPropertyName("MirrorChyanCdk")] public string EncryptedMirrorChyanCdk { get; set; } = "";
    public const string Version = "2.2.0-beta.5"; // 应用版本号

    // 新增快捷键设置
    public string ActivityHotkey { get; set; } = "F1"; // 活动 默认 F1
    public string ChronicleHotkey { get; set; } = "F2"; // 纪行 默认 F2
    public string WarpHotkey { get; set; } = "F3"; // 卡池 默认 F3
    public string GuideHotkey { get; set; } = "F4"; // 指南 默认 F4
    public string MapHotkey { get; set; } = "M"; // 地图 默认 M
    public string TechniqueHotkey { get; set; } = "E"; // 秘技 默认 E

}
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

// 继承 ObservableObject 获得属性通知能力
public partial class Cache : ObservableObject
{
    // 这些字段与UI绑定
    [ObservableProperty] private string _cdkStatus = "";

    [ObservableProperty] private string _cdkStatusForeground = "#F5222D";

    [ObservableProperty] private int _currentConfigIndex; // 当前配置索引

    [ObservableProperty] private string _currentConfigName = "Default"; // 当前配置名称

    [ObservableProperty] private string _startMode = "Current"; // 当前启动模式, "Current" 或 "All" 或 "Save Only"
    
    public AvaloniaList<string> ConfigNames { get; set; } = ["Default"]; // 配置名称列表
    
    public AvaloniaList<Strategy> Strategies { get; set; } = []; // 攻略列表

    // 以下字段无UI绑定
    public string HotfixVersion { get; set; } = ""; // 热更版本号
    public byte[]? UserGameResolution { get; set; } // 用户游戏分辨率设置的二进制数据
    public int? UserGameResolutionWidth { get; set; } // 用户游戏分辨率宽度
    public int? UserGameResolutionHeight { get; set; } // 用户游戏分辨率高度
    public int? UserGameFullscreenMode { get; set; } // 用户游戏全屏模式
    public bool NoNotifyForShortcut { get; set; } // 是否不再提示创建桌面快捷方式
    public long LastLaunchTimestamp { get; set; } // 上次启动时间戳
    public int LastViewAnnouncementId { get; set; } // 上次查看的公告ID
    
    // 以下字段不需要持久化存储，仅在运行时使用
    public bool IsGameResolutionChanged = false; // 游戏分辨率是否已更改
}
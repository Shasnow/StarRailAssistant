using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

// 继承 ObservableObject 获得属性通知能力
public partial class Cache : ObservableObject
{
    // 自动生成带通知的属性（字段名 _cdkStatus → 属性 CdkStatus）
    [ObservableProperty] private string _cdkStatus = "";

    [ObservableProperty] private string _cdkStatusForeground = "#F5222D";

    [ObservableProperty] private AvaloniaList<string> _configNames = ["Default"]; // 配置名称列表

    [ObservableProperty] private int _currentConfigIndex; // 当前配置索引

    [ObservableProperty] private string _currentConfigName = "Default"; // 当前配置名称
    
    [ObservableProperty] private string _startMode = "Current"; // 当前启动模式, "Current" 或 "All" 或 "Save Only"
    
    public string HotfixVersion { get; set; } =""; // 热更版本号
    
    public byte[]? UserGameResolution { get; set; } // 用户游戏分辨率设置的二进制数据
    public int? UserGameResolutionWidth { get; set; } // 用户游戏分辨率宽度
    public int? UserGameResolutionHeight { get; set; } // 用户游戏分辨率高度
    public int? UserGameFullscreenMode { get; set; } // 用户游戏全屏模式
    public bool NoNotifyForShortcut { get; set; } // 是否不再提示创建桌面快捷方式

    public bool IsGameResolutionChanged = false; // 游戏分辨率是否已更改
}
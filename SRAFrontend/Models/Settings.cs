using System.Text.Json.Serialization;

namespace SRAFrontend.Models;

public class Settings
{
    /// <summary>
    ///     是否启用线程安全模式 已过时，现在使用进程而非线程来防止阻塞
    /// </summary>
    public bool ThreadSafety { get; set; } = false;

    public double BackgroundOpacity { get; set; } = 0.9;
    public int Language { get; set; } = 1; // 0: English, 1: Simplified Chinese
    public double Zoom { get; set; } = 1; // 屏幕缩放比例
    public double ConfidenceThreshold { get; set; } = 0.9; // 识图置信度阈值
    public int DownloadChannel { get; set; } = 1; // 0: Mirror, 1: GitHub
    public int AppChannel { get; set; } // 0: stable, 1: beta
    public string MirrorChyanCdk { get; set; } = "";
    public bool EnableAutoUpdate { get; set; } = true; // 是否启用自动更新
    public string[] Proxies { get; set; } = ["https://tvv.tw/"]; // 代理列表
    public int DefaultPage { get; set; } = 0; // 启动时默认页面索引
    [JsonIgnore] public static string Version => "2.0.0"; // 应用版本号
    public bool AllowNotifications { get; set; } = true; // 是否允许通知
    public bool AllowSystemNotifications { get; set; } = true; // 是否允许系统通知
    public bool AllowEmailNotifications { get; set; } = false; // 是否允许邮件通知
    public bool EnableStartupLaunch { get; set; } = false; // 是否启用开机自启动
    public bool EnableMinimizeToTray { get; set; } = false; // 是否启用最小化到托盘
}
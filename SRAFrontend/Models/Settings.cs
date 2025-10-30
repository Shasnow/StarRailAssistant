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
    public double Zoom { get; set; } = 1;
    public double ConfidenceThreshold { get; set; } = 0.9;
    public int DownloadChannel { get; set; } = 1; // 0: Mirror, 1: GitHub
    public int AppChannel { get; set; } // 0: stable, 1: beta
    public string MirrorChyanCdk { get; set; } = "";
    public bool EnableAutoUpdate { get; set; } = true;
    public string[] Proxies { get; set; } = ["https://tvv.tw/"];
    public int DefaultPage { get; set; } = 0;
    [JsonIgnore] public static string Version => "2.0.0";
    public bool AllowNotifications { get; set; } = true;
    public bool AllowSystemNotifications { get; set; } = true;
    public bool AllowEmailNotifications { get; set; } = false;
    public bool EnableStartupLaunch { get; set; } = false;
    public bool EnableMinimizeToTray { get; set; } = false;
}
namespace SRAFrontend.Models;

public class ResolutionCache
{
    public byte[]? Resolution { get; set; } // 用户游戏分辨率设置的二进制数据
    public int? Width { get; set; } // 用户游戏分辨率宽度
    public int? Height { get; set; } // 用户游戏分辨率高度
    public int? FullscreenMode { get; set; } // 用户游戏全屏模式
}
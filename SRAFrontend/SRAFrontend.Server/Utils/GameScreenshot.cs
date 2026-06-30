using System.Runtime.InteropServices;
using System.Runtime.Versioning;

namespace SRAFrontend.Server.Utils;

/// <summary>
/// 通过 Win32 PrintWindow 后台截取游戏窗口（与 SRACore.operators.Operator._screenshot 同样的机制）。
/// 仅在 Windows 上可用；Server 与游戏运行在同一台机器，因此可直接抓取窗口。
/// </summary>
[SupportedOSPlatform("windows")]
public static class GameScreenshot
{
    private const string GameWindowTitle = "崩坏：星穹铁道";

    // PrintWindow flags
    private const uint PW_CLIENTONLY = 1;
    private const uint PW_RENDERFULLCONTENT = 2;

    /// <summary>
    /// 截取游戏窗口客户区，返回 PNG 字节；失败返回 null。
    /// </summary>
    public static byte[]? CaptureGameWindowPng()
    {
        var hwnd = FindWindow(null, GameWindowTitle);
        if (hwnd == IntPtr.Zero)
            return null;

        if (!GetClientRect(hwnd, out var rect))
            return null;

        int width = rect.Right - rect.Left;
        int height = rect.Bottom - rect.Top;
        if (width <= 0 || height <= 0)
            return null;

        IntPtr hdcWindow = GetWindowDC(hwnd);
        if (hdcWindow == IntPtr.Zero)
            return null;

        IntPtr hdcMem = IntPtr.Zero;
        IntPtr hBitmap = IntPtr.Zero;
        try
        {
            hdcMem = CreateCompatibleDC(hdcWindow);
            if (hdcMem == IntPtr.Zero)
                return null;

            hBitmap = CreateCompatibleBitmap(hdcWindow, width, height);
            if (hBitmap == IntPtr.Zero)
                return null;

            IntPtr oldObj = SelectObject(hdcMem, hBitmap);

            // PW_CLIENTONLY | PW_RENDERFULLCONTENT 适配游戏（DirectX/硬件渲染）窗口
            bool ok = PrintWindow(hwnd, hdcMem, PW_CLIENTONLY | PW_RENDERFULLCONTENT);
            SelectObject(hdcMem, oldObj);
            if (!ok)
                return null;

            return BitmapToPng(hBitmap, width, height);
        }
        finally
        {
            if (hBitmap != IntPtr.Zero) DeleteObject(hBitmap);
            if (hdcMem != IntPtr.Zero) DeleteDC(hdcMem);
            ReleaseDC(hwnd, hdcWindow);
        }
    }

    /// <summary>
    /// 从 HBITMAP 读取像素并编码为 PNG。手动写 BMP 头后用 GDI+ 转 PNG 不可控，
    /// 这里直接取 32 位 BGRA 像素，自行编码为 PNG（依赖 System.Drawing 在 Windows 可用）。
    /// </summary>
    private static byte[]? BitmapToPng(IntPtr hBitmap, int width, int height)
    {
        // 使用 System.Drawing.Common（Windows 平台内置可用）将 HBITMAP 转 PNG
        using var bmp = System.Drawing.Image.FromHbitmap(hBitmap);
        using var ms = new MemoryStream();
        bmp.Save(ms, System.Drawing.Imaging.ImageFormat.Png);
        return ms.ToArray();
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr FindWindow(string? lpClassName, string lpWindowName);

    [DllImport("user32.dll")]
    private static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);

    [DllImport("user32.dll")]
    private static extern IntPtr GetWindowDC(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);

    [DllImport("user32.dll")]
    private static extern bool PrintWindow(IntPtr hwnd, IntPtr hDC, uint nFlags);

    [DllImport("gdi32.dll")]
    private static extern IntPtr CreateCompatibleDC(IntPtr hdc);

    [DllImport("gdi32.dll")]
    private static extern IntPtr CreateCompatibleBitmap(IntPtr hdc, int width, int height);

    [DllImport("gdi32.dll")]
    private static extern IntPtr SelectObject(IntPtr hdc, IntPtr hgdiobj);

    [DllImport("gdi32.dll")]
    private static extern bool DeleteObject(IntPtr hObject);

    [DllImport("gdi32.dll")]
    private static extern bool DeleteDC(IntPtr hdc);
}

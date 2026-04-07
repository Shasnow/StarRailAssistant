using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Timers;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Threading;

namespace SRAFrontend.Controls;

public partial class OverlayWindow : Window
{
    private readonly Timer _followTimer = new(1000); // ~60fps
    private IntPtr _targetHwnd;
    public OverlayWindow()
    {
        InitializeComponent();
        _followTimer.Elapsed += (_, _) => Dispatcher.UIThread.Post(UpdatePosition);
    }

    protected override void OnOpened(EventArgs e)
    {
        base.OnOpened(e);
        SetMouseTransparent(); // 设置鼠标穿透
        StartFollow(GetWindowHandle(ProcessName));
    }

    public string ProcessName { get; init; } = Process.GetCurrentProcess().ProcessName;

    public bool EnabledMouseInfo
    {
        get => MousePosTextBlock.IsVisible;
        set => MousePosTextBlock.IsVisible = value;
    }

    protected override void OnClosed(EventArgs e)
    {
        base.OnClosed(e);
        StopFollow();
    }

    private static IntPtr GetWindowHandle(string processName)
    {
        var processes = Process.GetProcessesByName(processName);

        foreach (var process in processes)
        {
            if (process.MainWindowHandle != IntPtr.Zero && 
                process.MainWindowTitle.Length > 0)
            {
                return process.MainWindowHandle;
            }
        }
        return IntPtr.Zero;
    }

    private bool IsWindowActive(IntPtr hWnd) => User32.GetForegroundWindow() == hWnd;

    // 开始跟随
    private void StartFollow(IntPtr targetHwnd)
    {
        _targetHwnd = targetHwnd;
        _followTimer.Start();
    }

    private void StopFollow()
    {
        _followTimer.Stop();
        Hide();
    }

    // 跟随目标窗口位置大小
    private void UpdatePosition()
    {
        if (_targetHwnd == IntPtr.Zero || !User32.IsWindow(_targetHwnd))
        {
            StopFollow();
            return;
        }

        if (!IsWindowActive(_targetHwnd))
        {
            Hide();
            return;
        }
        Show();

        // 获取游戏客户区
        User32.GetClientRect(_targetHwnd, out var clientRect);
        User32.ClientToScreen(_targetHwnd, out var point);

        var x = point.X;
        var y = point.Y;
        var w = clientRect.Right - clientRect.Left;
        var h = clientRect.Bottom - clientRect.Top;
        // 过滤无效大小
        if (w <= 0 || h <= 0)
            return;

        Position = new PixelPoint(x, y);
        Width = w/RenderScaling;
        Height = h/RenderScaling;
        if (!EnabledMouseInfo) return;
        User32.GetCursorPos(out var cursor);
        var clientCursor = cursor;
        User32.ScreenToClient(_targetHwnd, ref clientCursor);

        // 限制在窗口内才显示
        var inWindow = clientCursor is { X: >= 0, Y: >= 0 } &&
                       clientCursor.X < w && clientCursor.Y < h;

        MousePosTextBlock.Text = inWindow 
            ? $"X:{clientCursor.X,4} Y:{clientCursor.Y,4}\nScale X:{clientCursor.X / (double)w:0.0000} Y:{clientCursor.Y / (double)h:0.0000}" 
            : "鼠标不在游戏窗口";
    }
    
    // 日志最大保留行数
    private readonly int _maxLogLines = 30;
    private readonly Queue<string> _logLines = new();

    public void AppendLog(string message)
    {

        _logLines.Enqueue(message);

        // 限制行数
        while (_logLines.Count > _maxLogLines)
            _logLines.Dequeue();

        // 拼接显示
        var sb = new StringBuilder();
        foreach (var line in _logLines)
            sb.AppendLine(line);

        LogText.Text = sb.ToString();
    }

    /// <summary>
    /// 设置鼠标事件穿透
    /// </summary>
    private void SetMouseTransparent()
    {
        var hwnd = TryGetPlatformHandle()?.Handle;
        if (hwnd == null) return;

        const int gwlExStyle = -20;
        const int wsExTransparent = 0x00000020;
        const int wsExLayered = 0x00080000;

        var exStyle = User32.GetWindowLongPtr(hwnd.Value, gwlExStyle);
        User32.SetWindowLongPtr(hwnd.Value, gwlExStyle, exStyle | wsExTransparent | wsExLayered);
    }
}

internal static class User32
{
    [StructLayout(LayoutKind.Sequential)]
    public struct Rect
    {
        public int Left, Top, Right, Bottom;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct Point
    {
        public int X;
        public int Y;
    }

    // 获得窗口客户区坐标（游戏真实显示区域）
    [DllImport("user32.dll")]
    public static extern bool GetClientRect(IntPtr hWnd, out Rect rect);

    // 客户区坐标转屏幕坐标
    [DllImport("user32.dll")]
    public static extern bool ClientToScreen(IntPtr hWnd, out Point lpPoint);

    [DllImport("user32.dll")]
    public static extern bool IsWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern IntPtr GetWindowLongPtr(IntPtr hWnd, int nIndex);

    [DllImport("user32.dll")]
    public static extern IntPtr SetWindowLongPtr(IntPtr hWnd, int nIndex, IntPtr dwNewLong);
    
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    
    [DllImport("user32.dll")]
    public static extern bool SendMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);
    
    [DllImport("user32.dll")]
    public static extern bool GetCursorPos(out Point lpPoint);

    [DllImport("user32.dll")]
    public static extern bool ScreenToClient(IntPtr hWnd, ref Point lpPoint);
}
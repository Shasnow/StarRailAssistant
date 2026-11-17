using Avalonia;
using System;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Platform;
using Avalonia.Styling;
using Avalonia.Threading;
using Avalonia.VisualTree;
using SRAFrontend.Desktop.ViewModels;
using SRAFrontend.Services;
using SukiUI.Controls;

namespace SRAFrontend.Desktop.Views;

public partial class MainWindow : SukiWindow
{
    private readonly SettingsService? _settingsService;

    public MainWindow() {}

    public MainWindow(SettingsService settingsService)
    {
        _settingsService = settingsService;
        InitializeComponent();
        // 命令面板需要截获输入框的 Esc/上下/回车，使用隧道阶段先于 TextBox 处理
        AddHandler(KeyDownEvent, OnWindowKeyDown, RoutingStrategies.Tunnel);
        // 深/浅色切换后重新计算命令面板配色
        ActualThemeVariantChanged += (_, _) => UpdatePaletteTheme();
        Closing += OnClosing;
    }

    /// <summary>
    /// 命令面板不依赖主题画刷（SukiUI 的画笔多为半透明），这里按当前基础主题写入实色画刷。
    /// </summary>
    private void UpdatePaletteTheme()
    {
        var dark = IsDarkTheme(ActualThemeVariant);
        var resources = Resources;
        resources["PaletteBackdropBrush"] = Brush(dark ? "#99000000" : "#59000000");
        resources["PalettePanelBrush"] = Brush(dark ? "#F21F1F1F" : "#F7F7F8");
        resources["PaletteBorderBrush"] = Brush(dark ? "#40FFFFFF" : "#22000000");
        resources["PaletteForegroundBrush"] = Brush(dark ? "#F5FFFFFF" : "#E6000000");
        resources["PaletteSecondaryForegroundBrush"] = Brush(dark ? "#99FFFFFF" : "#99000000");
        resources["PaletteInputBackgroundBrush"] = Brush(dark ? "#1AFFFFFF" : "#0F000000");
        resources["PaletteInputBorderBrush"] = Brush(dark ? "#40FFFFFF" : "#22000000");
    }

    /// <summary>跟随系统主题时（Default）按平台设置判断深浅色。</summary>
    private static bool IsDarkTheme(ThemeVariant variant)
    {
        if (variant == ThemeVariant.Dark) return true;
        if (variant == ThemeVariant.Light) return false;
        return Application.Current?.PlatformSettings?.GetColorValues().ThemeVariant == PlatformThemeVariant.Dark;
    }

    private static SolidColorBrush Brush(string color) => new(Color.Parse(color));

    private void OnWindowKeyDown(object? sender, KeyEventArgs e)
    {
        if (DataContext is not MainWindowViewModel viewModel) return;

        if (e.Key == Key.P &&
            e.KeyModifiers.HasFlag(KeyModifiers.Control) &&
            e.KeyModifiers.HasFlag(KeyModifiers.Shift))
        {
            TogglePalette(viewModel);
            e.Handled = true;
            return;
        }

        if (!viewModel.IsPaletteOpen) return;

        switch (e.Key)
        {
            case Key.Escape:
                viewModel.ClosePaletteCommand.Execute(null);
                e.Handled = true;
                break;
            case Key.Up:
                viewModel.MovePaletteSelection(-1);
                e.Handled = true;
                break;
            case Key.Down:
                viewModel.MovePaletteSelection(1);
                e.Handled = true;
                break;
            case Key.Enter:
                viewModel.RunSelectedPaletteCommand.Execute(null);
                e.Handled = true;
                break;
        }
    }

    private void TogglePalette(MainWindowViewModel viewModel)
    {
        if (viewModel.IsPaletteOpen)
        {
            viewModel.ClosePaletteCommand.Execute(null);
            return;
        }

        viewModel.OpenPaletteCommand.Execute(null);
        Dispatcher.UIThread.Post(() =>
        {
            PaletteSearchBox.Focus();
            PaletteSearchBox.SelectAll();
        });
    }

    /// <summary>只有点击遮罩本身（而非面板内部）时才关闭。</summary>
    private void OnPaletteBackdropPressed(object? sender, PointerPressedEventArgs e)
    {
        if (!ReferenceEquals(e.Source, sender)) return;
        if (DataContext is MainWindowViewModel viewModel)
            viewModel.ClosePaletteCommand.Execute(null);
    }

    private void OnPaletteListPointerReleased(object? sender, PointerReleasedEventArgs e)
    {
        if (e.InitialPressMouseButton != MouseButton.Left) return;
        if (e.Source is not Visual visual || visual.FindAncestorOfType<ListBoxItem>() is null) return;
        if (DataContext is MainWindowViewModel viewModel)
            viewModel.RunSelectedPaletteCommand.Execute(null);
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        UpdatePaletteTheme();
       
        if (_settingsService == null) return;
        var displaySettings = _settingsService.Settings.Display;
        if (displaySettings.IsRememberWindow)
        {
            var state = Enum.IsDefined(typeof(WindowState), displaySettings.WindowState)
                ? (WindowState)displaySettings.WindowState
                : WindowState.Normal;

            if (state is not (WindowState.Maximized or WindowState.FullScreen))
            {
                if (displaySettings is { WindowWidth: > 0, WindowHeight: > 0 })
                {
                    Width = displaySettings.WindowWidth;
                    Height = displaySettings.WindowHeight;
                }

                if (displaySettings.WindowPositionX != 0 || displaySettings.WindowPositionY != 0)
                {
                    Position = new PixelPoint(displaySettings.WindowPositionX, displaySettings.WindowPositionY);
                }
            }

            WindowState = state;
        }

        (DataContext as MainWindowViewModel)?.InitializeAsync();
    }

    private void OnClosing(object? sender, EventArgs e)
    {
        if (_settingsService == null) return;
        var displaySettings = _settingsService.Settings.Display;
        if (!displaySettings.IsRememberWindow) return;
        displaySettings.WindowState = (int)WindowState;
        if (WindowState is WindowState.FullScreen or WindowState.Maximized) return;
        // Don't update position and size if the window is maximized or full screen
        displaySettings.WindowPositionX = Position.X;
        displaySettings.WindowPositionY = Position.Y;
        displaySettings.WindowWidth = Width;
        displaySettings.WindowHeight = Height;
    }
}

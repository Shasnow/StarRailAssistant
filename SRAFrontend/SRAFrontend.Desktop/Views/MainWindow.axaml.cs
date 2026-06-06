using Avalonia;
using System;
using Avalonia.Interactivity;
using Avalonia.Controls;
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
        Closing += OnClosing;
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
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

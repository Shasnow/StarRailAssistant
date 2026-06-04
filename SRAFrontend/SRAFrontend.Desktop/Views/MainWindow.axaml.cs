using Avalonia;
using System;
using Avalonia.Interactivity;
using SRAFrontend.Desktop.ViewModels;
using SRAFrontend.Services;
using SukiUI.Controls;

namespace SRAFrontend.Desktop.Views;

public partial class MainWindow : SukiWindow
{
    private readonly SettingsService _settingsService;

    public MainWindow(SettingsService settingsService)
    {
        _settingsService = settingsService;
        InitializeComponent();
        Closed += OnClosed;
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        var displaySettings = _settingsService.Settings.Display;
        if (displaySettings.WindowWidth > 0 && displaySettings.WindowHeight > 0)
        {
            Width = displaySettings.WindowWidth;
            Height = displaySettings.WindowHeight;
        }

        if (displaySettings.WindowPositionX != 0 || displaySettings.WindowPositionY != 0)
        {
            Position = new PixelPoint((int)displaySettings.WindowPositionX, (int)displaySettings.WindowPositionY);
        }

        (DataContext as MainWindowViewModel)?.InitializeAsync();
    }

    private void OnClosed(object? sender, EventArgs e)
    {
        var displaySettings = _settingsService.Settings.Display;
        displaySettings.WindowPositionX = Position.X;
        displaySettings.WindowPositionY = Position.Y;
        displaySettings.WindowWidth = Width;
        displaySettings.WindowHeight = Height;
        _settingsService.Save();
    }
}

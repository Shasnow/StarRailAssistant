using Avalonia.Interactivity;
using Avalonia;
using SRAFrontend.Services;
using SRAFrontend.ViewModels;
using SukiUI.Controls;

namespace SRAFrontend.Views;

public partial class MainWindow : SukiWindow
{
    private readonly SettingsService _settingsService;

    public MainWindow()
    {
        InitializeComponent();
        _settingsService = App.ServiceProvider?.GetService<SettingsService>() 
            ?? throw new InvalidOperationException("SettingsService not available");
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        LoadWindowPosition();
        (DataContext as MainWindowViewModel)?.InitializeAsync();
    }

    protected override void OnClosing(WindowClosingEventArgs e)
    {
        SaveWindowPosition();
        base.OnClosing(e);
    }

    private void LoadWindowPosition()
    {
        var settings = _settingsService.Settings.Display;

        // 设置窗口位置
        Position = new PixelPoint((int)settings.WindowPositionX, (int)settings.WindowPositionY);
        
        // 设置窗口大小
        Width = settings.WindowSizeWidth;
        Height = settings.WindowSizeHeight;
    }

    private void SaveWindowPosition()
    {
        var settings = _settingsService.Settings.Display;

        var bounds = WindowState == WindowState.Normal ? new Rect(Position.X, Position.Y, Width, Height) : RestoreBounds;
        
        // 保存窗口位置
        settings.WindowPositionX = bounds.X;
        settings.WindowPositionY = bounds.Y;
        
        // 保存窗口大小
        settings.WindowSizeWidth = bounds.Width;
        settings.WindowSizeHeight = bounds.Height;

        _settingsService.Save();
    }
}

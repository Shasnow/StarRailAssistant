using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Desktop.Controls;
using SRAFrontend.Localization;
using SRAFrontend.Services;
using SRAFrontend.Utils;
using SukiUI;
using SukiUI.Controls;
using SukiUI.MessageBox;
using SukiUI.Toasts;

namespace SRAFrontend.Desktop.ViewModels;

public partial class MainWindowViewModel(
    IEnumerable<PageViewModel> pages,
    CommonModel commonModel,
    ActivityService activityService,
    AppService appService,
    ISukiToastManager toastManager)
    : ViewModelBase
{

    [ObservableProperty] private string _lightModeText =
        SukiTheme.GetInstance().ActiveBaseTheme.ToString() == "Light" ? "\uE472" : "\uE330";

    public string GreetingMessage => appService.GetPhrase();

    public ISukiToastManager ToastManager { get; init; } = toastManager;

    public IAvaloniaReadOnlyList<PageViewModel> Pages { get; } = new AvaloniaList<PageViewModel>(pages);

    /// <summary>
    ///     异步初始化方法，在应用启动时调用 (MainWindow.xaml.cs)
    /// </summary>
    public async Task InitializeAsync()
    {
        await commonModel.CleanupOldExeAsync();
        await commonModel.CheckAnnouncementAsync();
        await commonModel.CheckForUpdatesAsync();
        await commonModel.CheckDesktopShortcut();
    }

    [RelayCommand]
    private void SwitchLightMode()
    {
        SukiTheme.GetInstance().SwitchBaseTheme();
        LightModeText = SukiTheme.GetInstance().ActiveBaseTheme.ToString() == "Light" ? "\uE472" : "\uE330";
    }

    [RelayCommand]
    private static void OpenUrl(string url)
    {
        UrlUtil.OpenUrl(url);
    }

    [RelayCommand]
    private void ShowAnnouncementBoard()
    {
        commonModel.ShowAnnouncementBoard();
    }

    [RelayCommand]
    private void ShowActivity()
    {
        var viewModel = new ActivityPageViewModel(activityService);
        var view = new ActivityPageView { DataContext = viewModel };
        SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = "活动日历",
            Content = view
        });
    }
}

using System.Collections.Generic;
using System.Threading.Tasks;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Controls;
using SRAFrontend.Services;
using SRAFrontend.utilities;
using SukiUI;
using SukiUI.Controls;
using SukiUI.MessageBox;
using SukiUI.Toasts;

namespace SRAFrontend.ViewModels;

public partial class MainWindowViewModel(
    IEnumerable<PageViewModel> pages,
    CommonModel commonModel,
    ISukiToastManager toastManager,
    AnnouncementService announcementService)
    : ViewModelBase
{
    [ObservableProperty] private string _lightModeText =
        SukiTheme.GetInstance().ActiveBaseTheme.ToString() == "Light" ? "\uE472" : "\uE330";

    [ObservableProperty] private bool _titleBarVisible = true;

    /// <summary>
    /// 异步初始化方法，在应用启动时调用 (MainWindow.xaml.cs)
    /// </summary>
    public async Task InitializeAsync()
    {
        await commonModel.CheckForUpdatesAsync();
        // await commonModel.CheckAndFixPythonEnvironmentAsync();
        await commonModel.CheckDesktopShortcut();
    }

    public ISukiToastManager ToastManager { get; init; } = toastManager;

    public IAvaloniaReadOnlyList<PageViewModel> Pages { get; } = new AvaloniaList<PageViewModel>(pages);

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
        SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = "公告",
            Content = new AnnouncementBoardViewModel(announcementService)
        });
    }
}
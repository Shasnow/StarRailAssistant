using System.Collections.Generic;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Controls;
using SRAFrontend.Localization;
using SRAFrontend.Services;
using SRAFrontend.utilities;
using SukiUI;
using SukiUI.Controls;
using SukiUI.MessageBox;
using SukiUI.Toasts;

namespace SRAFrontend.ViewModels;

public partial class MainWindowViewModel : ViewModelBase
{
    private readonly AnnouncementService? _announcementService;

    [ObservableProperty] private string _lightModeText =
        SukiTheme.GetInstance().ActiveBaseTheme.ToString() == "Light" ? "\uE472" : "\uE330";

    [ObservableProperty] private bool _titleBarVisible = true;

    [ObservableProperty] private ISukiToastManager _toastManager;

    public MainWindowViewModel()
        // Design-time constructor
    {
    }

    public MainWindowViewModel(IEnumerable<PageViewModel> pages, ISukiToastManager toastManager,
        AnnouncementService announcementService)
    {
        _announcementService = announcementService;
        Pages = new AvaloniaList<PageViewModel>(pages);
        ToastManager = toastManager;
    }

    public string Greeting { get; } = Resources.GreetingText;

    public IAvaloniaReadOnlyList<PageViewModel> Pages { get; }
    
    public void SwitchLightMode()
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
            Header = "Announcements",
            Content = new AnnouncementBoardViewModel(_announcementService!)
        });
    }
}
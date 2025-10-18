using System.Collections.Generic;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Controls;
using SRAFrontend.utilities;
using SukiUI;
using SukiUI.Toasts;

namespace SRAFrontend.ViewModels;

public partial class MainWindowViewModel : ViewModelBase
{
    public string Greeting { get; } = Localization.Resources.GreetingText;

    [ObservableProperty]
    private string _lightModeText = SukiTheme.GetInstance().ActiveBaseTheme.ToString()=="Light"? "\uE330" : "\uE472";
    
    [ObservableProperty]
    private bool _titleBarVisible = true;
    
    [ObservableProperty]
    private ISukiToastManager _toastManager;
    
    public IAvaloniaReadOnlyList<PageViewModel> Pages { get; }

    public void SwitchLightMode()
    {
        SukiTheme.GetInstance().SwitchBaseTheme();
        LightModeText = SukiTheme.GetInstance().ActiveBaseTheme.ToString() == "Light" ? "\uE330" : "\uE472";
    }
    
    public MainWindowViewModel()
    // Design-time constructor
    {
        ToastManager=new SukiToastManager();
        ControlPanelViewModel controlPanelViewModel = new();
        Pages = new AvaloniaList<PageViewModel>(new HomePageViewModel(controlPanelViewModel), new TaskPageViewModel(ToastManager,controlPanelViewModel),new ExtensionPageViewModel(), new LogPageViewModel(), new SettingPageViewModel());
    }

    public MainWindowViewModel(IEnumerable<PageViewModel> pages, ISukiToastManager toastManager)
    {
        Pages = new AvaloniaList<PageViewModel>(pages);
        ToastManager = toastManager;
    }

    [RelayCommand]
    private static void OpenUrl(string url)
    {
        UrlUtil.OpenUrl(url);
    }
}
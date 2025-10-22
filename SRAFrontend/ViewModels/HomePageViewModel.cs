using CommunityToolkit.Mvvm.ComponentModel;
using SRAFrontend.Controls;
using SRAFrontend.Data;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;

public partial class HomePageViewModel(ControlPanelViewModel controlPanelViewModel, SettingsService settingsService) : PageViewModel(PageName.Home, "\uE2C2")
{
    public double ImageOpacity => settingsService.Settings.BackgroundOpacity;
    [ObservableProperty] private ControlPanelViewModel _controlPanelViewModel = controlPanelViewModel;
}
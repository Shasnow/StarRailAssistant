using CommunityToolkit.Mvvm.ComponentModel;
using SRAFrontend.Controls;
using SRAFrontend.Data;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;

public partial class HomePageViewModel(ControlPanelViewModel controlPanelViewModel, SettingsService settingsService) : PageViewModel(PageName.Home, "\uE2C2")
{
    public double ImageOpacity => settingsService.Settings.BackgroundOpacity;
    public double GlassCardOpacity => settingsService.Settings.CtrlPanelOpacity;
    public ControlPanelViewModel ControlPanelViewModel => controlPanelViewModel;
}
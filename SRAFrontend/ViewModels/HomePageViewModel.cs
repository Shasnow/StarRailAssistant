using CommunityToolkit.Mvvm.ComponentModel;
using SRAFrontend.Controls;
using SRAFrontend.Data;

namespace SRAFrontend.ViewModels;

public partial class HomePageViewModel(ControlPanelViewModel controlPanelViewModel) : PageViewModel(PageName.Home, "\uE2C2")
{
    public double ImageOpacity => 0.9;
    [ObservableProperty] private ControlPanelViewModel _controlPanelViewModel = controlPanelViewModel;
}
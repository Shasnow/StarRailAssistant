using CommunityToolkit.Mvvm.ComponentModel;
using SRAFrontend.Data;

namespace SRAFrontend.ViewModels;

public partial class PageViewModel(PageName pageName, string iconText) : ViewModelBase
{
    [ObservableProperty]
    private PageName _pageName = pageName;
    [ObservableProperty]
    private string _displayName = Localization.Resources.ResourceManager.GetString(pageName+"Text")!;

    [ObservableProperty] private string _iconText = iconText;
}
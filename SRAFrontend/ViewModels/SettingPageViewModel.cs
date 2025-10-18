using CommunityToolkit.Mvvm.ComponentModel;
using SRAFrontend.Data;

namespace SRAFrontend.ViewModels;

public partial class SettingPageViewModel(): PageViewModel(PageName.Setting, "\uE272")
{
    public int CurrentLang
    {
        get
        {
            return Localization.Resources.Culture?.Name switch
            {
                "zh-Hans" => 1,
                _ => 0
            };
        }
    }

    [ObservableProperty]
    private double _zoom;
}
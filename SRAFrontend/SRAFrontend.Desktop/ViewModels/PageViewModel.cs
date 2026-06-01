using SRAFrontend.Data;
using SRAFrontend.Localization;

namespace SRAFrontend.ViewModels;

public partial class PageViewModel(PageName pageName, string iconText) : ViewModelBase
{
    public string DisplayName =>
        Resources.ResourceManager.GetString(pageName + "Text", Resources.Culture) ??
        pageName.ToString();

    public string IconText => iconText;
}
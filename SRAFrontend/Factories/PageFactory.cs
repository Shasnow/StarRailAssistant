using System;
using SRAFrontend.Data;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Factories;

public class PageFactory(Func<PageName, PageViewModel> factory)
{
    public PageViewModel GetPageViewModel(PageName pageName)
    {
        return factory.Invoke(pageName);
    }
}
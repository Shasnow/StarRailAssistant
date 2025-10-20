using CommunityToolkit.Mvvm.ComponentModel;
using SRAFrontend.Data;

namespace SRAFrontend.ViewModels;

public partial class LogPageViewModel(): PageViewModel(PageName.Log, "\uEAFE")
{
    [ObservableProperty] private string _log = " 2024-06-01 12:00:00 [信息] 应用程序启动成功。";
}
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Data;
using SRAFrontend.Services;

namespace SRAFrontend.Desktop.ViewModels;

public partial class ExtensionPageViewModel(IBackendService backendService)
    : PageViewModel(PageName.Extension, "\uE596")
{
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(IsEmpty))]
    private bool _isLoadingExtensions;

    public ObservableCollection<ExtensionCardViewModel> Extensions { get; } = [];

    /// <summary>当前已加载的扩展数量，用于标题栏的计数徽标。</summary>
    public int ExtensionCount => Extensions.Count;

    /// <summary>列表为空且不在加载中时展示空状态，避免加载瞬间闪现空状态。</summary>
    public bool IsEmpty => Extensions.Count == 0 && !IsLoadingExtensions;

    /// <summary>
    /// 自动加载（页面导航时调用）
    /// </summary>
    [RelayCommand]
    private async Task LoadExtensionsAsync()
    {
        if (Extensions.Count > 0)
            return;
        await RefreshExtensionsAsync();
    }

    /// <summary>
    /// 手动刷新（用户点击刷新按钮），无视缓存
    /// </summary>
    [RelayCommand]
    private async Task RefreshExtensionsAsync()
    {
        if (IsLoadingExtensions) return;
        IsLoadingExtensions = true;
        try
        {
            var extensions = await backendService.GetExtensionsAsync();
            Extensions.Clear();
            foreach (var info in extensions)
                Extensions.Add(new ExtensionCardViewModel(info, backendService));
        }
        finally
        {
            IsLoadingExtensions = false;
            OnPropertyChanged(nameof(ExtensionCount));
            OnPropertyChanged(nameof(IsEmpty));
        }
    }
}

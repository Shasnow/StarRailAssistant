using System.IO;
using System.Threading.Tasks;
using Avalonia.Media.Imaging;
using CommunityToolkit.Mvvm.ComponentModel;
using SRAFrontend.Data;
using SRAFrontend.Desktop.Controls;
using SRAFrontend.Services;

namespace SRAFrontend.Desktop.ViewModels;

public partial class HomePageViewModel(
    ControlPanelViewModel controlPanelViewModel,
    SettingsService settingsService,
    AppService appService)
    : PageViewModel(PageName.Home, "\uE2C2")
{
    private byte[]? _currentSource;
    private Bitmap? _currentBitmap;

    [ObservableProperty] private Bitmap? _backgroundImage;
    [ObservableProperty] private bool _isLoadingImage;

    public async Task UpdateBackgroundImageAsync()
    {
        IsLoadingImage = true;
        var bytes = await appService.GetBackgroundImageAsync();
        // AppService 缓存了 byte[]，同一数据源直接复用已解码的 Bitmap，避免重复解码与泄漏
        if (!ReferenceEquals(bytes, _currentSource))
        {
            _currentBitmap?.Dispose();
            _currentBitmap = new Bitmap(new MemoryStream(bytes));
            _currentSource = bytes;
        }
        BackgroundImage = _currentBitmap;
        IsLoadingImage = false;
    }

    public double ImageOpacity => settingsService.Settings.Display.BackgroundOpacity;
    public double GlassCardOpacity => settingsService.Settings.Display.ControlPanelOpacity;
    public ControlPanelViewModel ControlPanelViewModel => controlPanelViewModel;
}

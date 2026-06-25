using System.Threading.Tasks;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.Desktop.ViewModels;

public partial class ExtensionPageViewModel(IBackendService backendService, SettingsService settingsService) : PageViewModel(PageName.Extension, "\uE596")
{
    private bool _enableAutoPlot;

    private bool _skipPlot;

    public WarpForecastSettings WarpForecastSettings => settingsService.Settings.WarpForecast;

    public bool EnableAutoPlot
    {
        get => _enableAutoPlot;
        set
        {
            _enableAutoPlot = value;
            OnPropertyChanged();
            _ = backendService.SendInputAsync(value ? "trigger enable AutoPlotTrigger" : "trigger disable AutoPlotTrigger");
        }
    }

    public bool SkipPlot
    {
        get => _skipPlot;
        set
        {
            _skipPlot = value;
            OnPropertyChanged();
            _ = backendService.SendInputAsync($"trigger set AutoPlotTrigger skip_plot --type bool {value}");
        }
    }

    [RelayCommand]
    private async Task RunWarpForecastAsync()
    {
        await backendService.TaskSingleAsync("WarpForecastTask");
    }
}

using SRAFrontend.Data;
using SRAFrontend.Services;

namespace SRAFrontend.Desktop.ViewModels;

public class ExtensionPageViewModel(IBackendService backendService) : PageViewModel(PageName.Extension, "\uE596")
{
    private bool _enableAutoPlot;

    private bool _skipPlot;

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
            _ = backendService.SendInputAsync($"trigger set --type AutoPlotTrigger skip_plot {value}");
        }
    }
}
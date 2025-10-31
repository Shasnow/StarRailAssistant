using SRAFrontend.Data;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;

public class ExtensionPageViewModel(SraService sraService) : PageViewModel(PageName.Extension, "\uE596")
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
            sraService.SendInput(value ? "trigger enable AutoPlotTrigger" : "trigger disable AutoPlotTrigger");
        }
    }

    public bool SkipPlot
    {
        get => _skipPlot;
        set
        {
            _skipPlot = value;
            OnPropertyChanged();
            sraService.SendInput($"trigger set-bool AutoPlotTrigger SkipPlot {value}");
        }
    }
}
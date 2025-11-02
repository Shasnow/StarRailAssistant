using SRAFrontend.Data;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;

public class ConsolePageViewModel : PageViewModel
{
    private readonly SraService _sraService;

    public ConsolePageViewModel(SraService sraService) : base(PageName.Console, "\uEAE8")
    {
        _sraService = sraService;
        _sraService.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName == nameof(SraService.Output))
            {
                OnPropertyChanged(nameof(LogText));
            }
        };
    }

    public string LogText => _sraService.Output;

    public void SendInput(string input)
    {
        _sraService.SendInput(input);
    }
}
using System.Linq;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using SRAFrontend.Data;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;

public partial class ConsolePageViewModel : PageViewModel
{
    private readonly SraService _sraService;

    public ConsolePageViewModel(SraService sraService) : base(PageName.Console, "\uEAE8")
    {
        _sraService = sraService;
        _sraService.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName == nameof(SraService.OutputLines))
            {
                OnPropertyChanged(nameof(LogText));
            }
        };
        FilterOptions.CollectionChanged+= (_, _) =>
        {
            OnPropertyChanged(nameof(LogText));
        };
    }

    public string LogText
    {
        get
        {
            // 无需判断 null（已知 OutputLines 非空）
            var lines = _sraService.OutputLines;
            var filteredLines = lines.Where(line =>
            {
                // 过滤 null 行（避免 Contains 空引用）
                if (line == null)
                    return false;
                // 1. 检查是否匹配已勾选的级别（标识可能在任意位置，用 Contains）
                for (var i = 0; i < _levelPrefixes.Length; i++)
                {
                    // 勾选了该级别，且日志行包含对应标识 → 保留
                    if (FilterOptions[i] && line.Contains(_levelPrefixes[i]))
                    {
                        return true;
                    }
                }
                // 2. 保留无任何级别标识的日志（无匹配级别时默认保留）
                var hasAnyLevelPrefix = _levelPrefixes.Any(line.Contains);
                return !hasAnyLevelPrefix;
            });
            return string.Join('\n', filteredLines);
        }
    }

    private readonly string[] _levelPrefixes = ["TRACE", "DEBUG", "INFO", "WARN", "ERROR"];
    
    [ObservableProperty]
    private AvaloniaList<bool> _filterOptions = [false, true, true, true, true]; // TRACE, DEBUG, INFO, WARN, ERROR

    public void SendInput(string input)
    {
        _sraService.SendInput(input);
    }
}
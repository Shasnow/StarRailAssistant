using System.Linq;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Data;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;

public partial class ConsolePageViewModel : PageViewModel
{
    private readonly SraService _sraService;
    private readonly AvaloniaList<string> _consoleLines = [];
    
    private const int MaxConsoleLines = 1000;

    public ConsolePageViewModel(SraService sraService) : base(PageName.Console, "\uEAE8")
    {
        _sraService = sraService;
        _sraService.Outputted += AddConsoleLine;
        _sraService.StartSraProcess("--inline");
        FilterOptions.CollectionChanged+= (_, _) => OnPropertyChanged(nameof(ConsoleLines));
    }

    public string ConsoleLines
    {
        get
        {
            var filteredLines = _consoleLines.Where(line =>
            {
                // 1. 检查是否匹配已勾选的级别（标识可能在任意位置，用 Contains）
                for (var i = 0; i < _levelPrefixes.Length; i++)
                {
                    // 勾选了该级别，且日志行包含对应标识 → 保留
                    if (FilterOptions[i] && line.Contains(_levelPrefixes[i]))
                        return true;
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
    private AvaloniaList<bool> _filterOptions = [false, false, true, true, true]; // TRACE, DEBUG, INFO, WARN, ERROR
    
    private void AddConsoleLine(string line)
    {
        // 添加新行到列表末尾
        _consoleLines.Add(line.Trim());
        // 超出最大行数时，移除最前面的旧行
        if (_consoleLines.Count > MaxConsoleLines) _consoleLines.RemoveAt(0);
        // 触发UI更新
        OnPropertyChanged(nameof(ConsoleLines));
    }
    
    private void HandleMessage(string message)
    {
        _sraService.SendInput(message);
    }
    
    private void HandleCommand(string line)
    {
        var parts = line.Split(' ', 2);
        var command = parts[0].ToLower();
        // var args = parts.Length > 1 ? parts[1] : string.Empty;
        switch (command)
        {
            case "connect":
                AddConsoleLine("未来版本支持WebSocket连接命令");
                break;
            case "disconnect":
                AddConsoleLine("未连接到任何WebSocket服务器");
                break;
            default:
                AddConsoleLine($"未知命令: {command}");
                break;
        }
    }

    public void HandleInput(string input)
    {
        if (input.StartsWith('/'))
        {
            HandleCommand(input[1..]);
        }
        else
        {
            HandleMessage(input);
        }
    }

    [RelayCommand]
    private void RestartConsole()
    {
        _consoleLines.Clear();
        _sraService.RestartSraProcess("--inline");
    }
}
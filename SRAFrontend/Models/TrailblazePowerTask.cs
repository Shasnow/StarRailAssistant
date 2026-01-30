using System;
using System.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace SRAFrontend.Models;

public partial class TrailblazePowerTask(Action<TrailblazePowerTask> onAddTaskItem) : ObservableObject
{
    public int MaxSingleTimes { get; init; } // 最大单次挑战次数

    [ObservableProperty] private int _count = 1;

    [ObservableProperty] private IEnumerable? _levels;

    [ObservableProperty] private int _runTimes = 1;

    [ObservableProperty] private int _selectedIndex;

    [ObservableProperty] private bool _canAutoDetect = true;

    [ObservableProperty] private bool _isAutoDetect;

    public string Title { get; init; } = string.Empty;
    public int Cost { get; init; }
    public string? CostText { get; init; }  // 自定义消耗显示文本，如 "10-40"
    public string HeaderText => CostText != null
        ? $"{Title} (单次消耗: {CostText})"
        : $"{Title} (单次消耗: {Cost})";

    [RelayCommand]
    private void AddTaskItem()
    {
        onAddTaskItem.Invoke(this);
    }
}
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

    public string Title { get; init; } = string.Empty;
    public int Cost { get; init; }
    public string HeaderText => $"{Title} (单次消耗: {Cost})";

    [RelayCommand]
    private void AddTaskItem()
    {
        onAddTaskItem.Invoke(this);
    }
}
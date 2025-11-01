using System;
using System.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace SRAFrontend.Models;

public partial class TrailblazePowerTask(Action<TrailblazePowerTask> onAddTaskItem) : ObservableObject
{
    public bool CanMulti { get; init; }

    [ObservableProperty] private int _count = 1;

    [ObservableProperty] private IEnumerable? _levels;

    [ObservableProperty] private int _runTimes;

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
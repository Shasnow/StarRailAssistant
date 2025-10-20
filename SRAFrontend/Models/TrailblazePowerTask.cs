using System;
using System.Collections;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Models;

public partial class TrailblazePowerTask(Action<TrailblazePowerTask> onAddTaskItem) : ViewModelBase
{
    [ObservableProperty] private bool _canMulti;

    [ObservableProperty] private int _count = 1;

    [ObservableProperty] private IEnumerable? _levels;

    [ObservableProperty] private int _runTimes;

    [ObservableProperty] private int _selectedIndex;

    [ObservableProperty] private string _title = string.Empty;

    [RelayCommand]
    private void AddTaskItem()
    {
        onAddTaskItem.Invoke(this);
    }
}
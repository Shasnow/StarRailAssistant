using System;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Controls;

public partial class ControlPanelViewModel:ViewModelBase
{
    [ObservableProperty]
    private string _startMode = "Current"; // Current, All
    [ObservableProperty]
    private int _selectedIndex;

    [RelayCommand]
    private void SwitchStartMode(string mode)
    {
        StartMode = mode;
    }

    [RelayCommand]
    private void Start()
    {
        Console.Out.WriteLine("Successfully started tasks in " + StartMode + " mode.");
    }
}
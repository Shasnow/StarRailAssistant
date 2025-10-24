using System;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Services;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Controls;

public partial class ControlPanelViewModel(SraService sraService):ViewModelBase
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
        try
        {
            sraService.SendInput("");
        }
        catch (Exception e)
        {
            File.AppendAllText("error.log", DateTime.Now + " : " + e.Message + Environment.NewLine + e.StackTrace);
        }
    }
}
using System;
using System.IO;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Services;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Controls;

public partial class ControlPanelViewModel(SraService sraService, CacheService cacheService):ViewModelBase
{
    [ObservableProperty]
    private string _startMode = "Current"; // Current, All

    public int SelectedConfigIndex 
    {
        get=>cacheService.Cache.SelectedConfigIndex;
        set
        {
            cacheService.Cache.SelectedConfigIndex = value;
            OnPropertyChanged();
        }
    }

    [ObservableProperty]
    private AvaloniaList<string> _configNames=cacheService.Cache.ConfigNames; 

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
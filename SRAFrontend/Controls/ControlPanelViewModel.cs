using System;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Controls;

public partial class ControlPanelViewModel :ViewModelBase
{
    [ObservableProperty]
    private string _startMode = "Current"; // Current, All
    [ObservableProperty] private bool _isAddConfigOpen;
    [ObservableProperty] private string _newConfigName = "";
    private readonly SraService _sraService;
    private readonly CacheService _cacheService;

    /// <inheritdoc/>
    public ControlPanelViewModel(SraService sraService, CacheService cacheService)
    {
        _sraService = sraService;
        _cacheService = cacheService;
        _sraService.PropertyChanged+= (_, args) =>
        {
            if (args.PropertyName == nameof(SraService.IsRunning))
            {
                OnPropertyChanged(nameof(CanStart));
            }
        };
    }
    
    public bool CanStart => !_sraService.IsRunning;

    public Cache Cache => _cacheService.Cache;
    
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
            _sraService.TaskRun(StartMode=="All"? null : Cache.CurrentConfigName);
        }
        catch (Exception e)
        {
            File.AppendAllText("error.log", DateTime.Now + " : " + e.Message + Environment.NewLine + e.StackTrace);
        }
    }
    
    [RelayCommand]
    private void OpenAddConfig()
    { 
        IsAddConfigOpen = true;
    }
    [RelayCommand]
    private void AddConfig()
    {
        if (string.IsNullOrWhiteSpace(NewConfigName))
            return;
        
        Cache.ConfigNames.Add(NewConfigName);
        NewConfigName = "";
        IsAddConfigOpen = false;
    }

    [RelayCommand]
    private void RemoveConfig()
    {
        if (Cache.ConfigNames.Count==1)
        {
            return;
        }
        Cache.ConfigNames.RemoveAt(Cache.CurrentConfigIndex);
        Cache.CurrentConfigIndex = 0;
    }
}
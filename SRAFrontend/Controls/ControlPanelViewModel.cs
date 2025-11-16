using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Controls;

public partial class ControlPanelViewModel : ViewModelBase
{
    private readonly CacheService _cacheService;
    private readonly ConfigService _configService;
    private readonly SettingsService _settingsService;
    private readonly SraService _sraService;
    [ObservableProperty] private bool _isAddConfigOpen;
    [ObservableProperty] private string _newConfigName = "";

    public ControlPanelViewModel(SraService sraService, CacheService cacheService, ConfigService configService,
        SettingsService settingsService)
    {
        _settingsService = settingsService;
        _configService = configService;
        _sraService = sraService;
        _cacheService = cacheService;
        _sraService.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName == nameof(SraService.IsRunning)) OnPropertyChanged(nameof(CanStart));
        };
    }

    public bool CanStart => !_sraService.IsRunning;

    public Cache Cache => _cacheService.Cache;

    [RelayCommand]
    private void SwitchStartMode(string mode)
    {
        Cache.StartMode = mode;
    }

    [RelayCommand]
    private void StartButton()
    {
        switch (Cache.StartMode)
        {
            case "Current":
                Save();
                _sraService.TaskRun(Cache.CurrentConfigName);
                break;
            case "All":
                Save();
                _sraService.TaskRun(null);
                break;
            case "Save Only":
                Save();
                break;
        }
    }

    [RelayCommand]
    private void StopButton()
    {
        _sraService.TaskStop();
    }

    private void Save()
    {
        _cacheService.SaveCache();
        _configService.SaveConfig();
        _settingsService.SaveSettings();
    }

    [RelayCommand]
    private void OpenAddConfig()
    {
        IsAddConfigOpen = true;
    }

    [RelayCommand]
    private void AddConfig()
    {
        IsAddConfigOpen = false;
        if (string.IsNullOrWhiteSpace(NewConfigName))
            return;

        Cache.ConfigNames.Add(NewConfigName);
        NewConfigName = "";
    }

    [RelayCommand]
    private void RemoveConfig()
    {
        if (Cache.ConfigNames.Count == 1) return;
        Cache.ConfigNames.RemoveAt(Cache.CurrentConfigIndex);
        Cache.CurrentConfigIndex = 0;
    }
}
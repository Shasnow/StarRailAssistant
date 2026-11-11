using System;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Desktop.ViewModels;
using SRAFrontend.Localization;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.Desktop.Controls;

public partial class ControlPanelViewModel : ViewModelBase
{
    private readonly CacheService _cacheService;
    private readonly ConfigService _configService;
    private readonly SettingsService _settingsService;
    private readonly IBackendService _backendService;
    private readonly CommonModel _commonModel;
    [ObservableProperty] private bool _isAddConfigOpen;
    [ObservableProperty] private string _newConfigName = "";

    /// <summary>
    /// 开始按钮与停止按钮在控制面板上占据同一位置，任务启动后立即互换显示：
    /// 连击（或点击被游戏窗口激活流程“吞噬”的重复点击）会落到刚出现的停止按钮上，
    /// 导致任务刚启动就被停止。启动后的短时间内忽略停止请求。
    /// </summary>
    private static readonly TimeSpan StopGuardWindow = TimeSpan.FromSeconds(2);

    private DateTime _lastStartRequestUtc = DateTime.MinValue;

    public ControlPanelViewModel(
        IBackendService backendService,
        CacheService cacheService,
        ConfigService configService,
        SettingsService settingsService,
        CommonModel commonModel)
    {
        _settingsService = settingsService;
        _configService = configService;
        _backendService = backendService;
        _cacheService = cacheService;
        _commonModel = commonModel;
        _backendService.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName == nameof(IBackendService.IsTaskRunning)) OnPropertyChanged(nameof(CanStart));
        };
    }

    public string StartModeText
    {
        get
        {
            return Cache.StartMode switch
            {
                "Current" => Resources.CurrentText,
                "All" => Resources.AllText,
                "Save Only" => Resources.SaveOnlyText,
                _ => Resources.UnknownText
            };
        }
    }

    public bool CanStart => !_backendService.IsTaskRunning;

    public Cache Cache => _cacheService.Cache;

    [RelayCommand]
    private void SwitchStartMode(string mode)
    {
        Cache.StartMode = mode;
        OnPropertyChanged(nameof(StartModeText));
    }

    [RelayCommand]
    private async Task StartButton()
    {
        switch (Cache.StartMode)
        {
            case "Current":
                Save();
                _lastStartRequestUtc = DateTime.UtcNow;
                if (await _backendService.TaskRunAsync(Cache.CurrentConfigName))
                    _commonModel.ShowSuccessToast(Resources.TaskStartSuccessMessage, string.Format(Resources.Culture, Resources.ConfigurationStartedMessage, Cache.CurrentConfigName));
                else
                    _commonModel.ShowErrorToast(Resources.TaskStartFailedError, string.Format(Resources.Culture, Resources.ConfigurationStartFailedError, Cache.CurrentConfigName));
                break;
            case "All":
                Save();
                _lastStartRequestUtc = DateTime.UtcNow;
                if (await _backendService.TaskRunAsync(null))
                    _commonModel.ShowSuccessToast(Resources.TaskStartSuccessMessage, Resources.AllConfigurationsStartedMessage);
                else
                    _commonModel.ShowErrorToast(Resources.TaskStartFailedError, Resources.AllConfigurationsStartFailedError);
                break;
            case "Save Only":
                Save();
                _commonModel.ShowSuccessToast(Resources.SaveSuccessMessage, Resources.ConfigurationSavedMessage);
                break;
        }
    }
    
    public async Task StartSingleTask(string configName)
    {
        Save();
        _lastStartRequestUtc = DateTime.UtcNow;
        if (await _backendService.TaskSingleAsync(configName, null))
            _commonModel.ShowSuccessToast(Resources.TaskStartSuccessMessage, Resources.TaskStartedMessage);
        else
            _commonModel.ShowErrorToast(Resources.TaskStartFailedError, Resources.TaskStartBackendErrorMessage);
    }

    [RelayCommand]
    private async Task StopButton()
    {
        // 刚发出启动请求时忽略停止，避免点击落到互换位置后的停止按钮上（任务启动即停止）
        if (DateTime.UtcNow - _lastStartRequestUtc < StopGuardWindow) return;
        await _backendService.TaskStopAsync();
    }

    private void Save()
    {
        _cacheService.SaveCache();
        _configService.Save();
        // _settingsService.Save();
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
        if (NewConfigName.IndexOfAny(['\\', '/', ':', '*', '?', '"', '<', '>', '|']) != -1)
        {
            _commonModel.ShowErrorToast(Resources.InvalidConfigurationNameError, Resources.InvalidConfigurationNameCharsMessage);
            return;
        }
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
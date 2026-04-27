using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Localization;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Controls;

public partial class ControlPanelViewModel : ViewModelBase
{
    private readonly CacheService _cacheService;
    private readonly ConfigService _configService;
    private readonly SettingsService _settingsService;
    private readonly IBackendService _backendService;
    private readonly CommonModel _commonModel;
    [ObservableProperty] private bool _isAddConfigOpen;
    [ObservableProperty] private string _newConfigName = "";

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
    private void StartButton()
    {
        switch (Cache.StartMode)
        {
            case "Current":
                Save();
                if (_backendService.TaskRun(Cache.CurrentConfigName))
                    _commonModel.ShowSuccessToast("任务启动成功", $"已启动配置：{Cache.CurrentConfigName}");
                else
                    _commonModel.ShowErrorToast("任务启动失败", $"无法启动配置：{Cache.CurrentConfigName}，请检查后端状态。");
                break;
            case "All":
                Save();
                if (_backendService.TaskRun(null))
                    _commonModel.ShowSuccessToast("任务启动成功", "已启动所有配置任务。");
                else
                    _commonModel.ShowErrorToast("任务启动失败", "无法启动所有配置任务，请检查后端状态。");
                break;
            case "Save Only":
                Save();
                _commonModel.ShowSuccessToast("保存成功", "已保存当前配置。");
                break;
        }
    }
    
    public void StartSingleTask(string configName)
    {
        Save();
        if (_backendService.TaskSingle(configName))
            _commonModel.ShowSuccessToast("任务启动成功", "已启动任务");
        else
            _commonModel.ShowErrorToast("任务启动失败", "无法启动任务，请检查后端状态。");
    }

    [RelayCommand]
    private void StopButton()
    {
        _backendService.TaskStop();
    }

    private void Save()
    {
        _cacheService.SaveCache();
        _configService.SaveConfig();
        _settingsService.Save();
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
            _commonModel.ShowErrorToast("无效的配置名称", "配置名称不能包含以下字符：\\ / : * ? \" < > |");
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
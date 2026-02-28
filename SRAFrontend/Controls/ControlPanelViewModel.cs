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
    private readonly SraService _sraService;
    private readonly CommonModel _commonModel;
    [ObservableProperty] private bool _isAddConfigOpen;
    [ObservableProperty] private string _newConfigName = "";

    public ControlPanelViewModel(
        SraService sraService,
        CacheService cacheService,
        ConfigService configService,
        SettingsService settingsService,
        CommonModel commonModel)
    {
        _settingsService = settingsService;
        _configService = configService;
        _sraService = sraService;
        _cacheService = cacheService;
        _commonModel = commonModel;
        _sraService.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName == nameof(SraService.IsRunning)) OnPropertyChanged(nameof(CanStart));
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

    public bool CanStart => !_sraService.IsRunning;

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
                if (_sraService.TaskRun(Cache.CurrentConfigName))
                    _commonModel.ShowSuccessToast("任务启动成功", $"已启动配置：{Cache.CurrentConfigName}");
                else
                    _commonModel.ShowErrorToast("任务启动失败", $"无法启动配置：{Cache.CurrentConfigName}，请检查后端状态。");
                break;
            case "All":
                Save();
                if (_sraService.TaskRun(null))
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
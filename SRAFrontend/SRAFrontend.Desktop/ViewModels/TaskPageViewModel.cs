using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Platform.Storage;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Data;
using SRAFrontend.Desktop.Controls;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SukiUI.Controls;
using SukiUI.MessageBox;

namespace SRAFrontend.Desktop.ViewModels;

public partial class TaskPageViewModel : PageViewModel
{
    private readonly CacheService _cacheService;
    private readonly CommonModel _commonModel;
    private readonly ConfigService _configService;
    private readonly IBackendService _backendService;
    private TpTask[] _tpTasks = [];

    [ObservableProperty]
    [NotifyPropertyChangedFor(
        nameof(CosmicStrifeConfig), 
        nameof(MissionAccomplishedConfig),
        nameof(ReceiveRewardsConfig),
        nameof(StartGameConfig),
        nameof(TrailblazePowerConfig),
        nameof(SelectedGardenOfPlentyLevels1Index),
        nameof(SelectedGardenOfPlentyLevels2Index),
        nameof(SelectedPlanarFissureLevelsIndex),
        nameof(SelectedRealmOfTheStrangeLevelsIndex))]
    private TasksConfig _currentConfig;

    [ObservableProperty] private bool _isTpTaskAutoDetect;

    [ObservableProperty] [NotifyPropertyChangedFor(nameof(EnableContextMenu))]
    private object? _selectedTaskItem;

    [ObservableProperty] [NotifyPropertyChangedFor(nameof(CurrentTpTaskLevels), nameof(CurrentTpTaskMaxSingleTimes))]
    private int _selectedTpTaskIndex;

    public int SelectedGardenOfPlentyLevels1Index
    {
        get => TrailblazePowerConfig.GardenOfPlentyLevel1-1;
        set
        {
            TrailblazePowerConfig.GardenOfPlentyLevel1 = value+1;
            OnPropertyChanged();
        }
    }
    public int SelectedGardenOfPlentyLevels2Index
    {
        get => TrailblazePowerConfig.GardenOfPlentyLevel2-1;
        set
        {
            TrailblazePowerConfig.GardenOfPlentyLevel2 = value+1;
            OnPropertyChanged();
        }
    }

    public int SelectedPlanarFissureLevelsIndex
    {
        get => TrailblazePowerConfig.PlanarFissureLevel-1;
        set
        {
            TrailblazePowerConfig.PlanarFissureLevel = value+1;
            OnPropertyChanged();
        }
    }

    public int SelectedRealmOfTheStrangeLevelsIndex
    {
        get =>  TrailblazePowerConfig.RealmOfTheStrangeLevel-1;
        set
        {
            TrailblazePowerConfig.RealmOfTheStrangeLevel = value+1;
            OnPropertyChanged();
        }
    }

    [ObservableProperty] private TpTaskLevel? _selectedTpTaskLevel;

    [ObservableProperty] private int _tpTaskRunTimes = 1;

    [ObservableProperty] private int _tpTaskSingleTimes = 1;

    public TaskPageViewModel(
        CommonModel commonModel,
        ControlPanelViewModel controlPanelViewModel,
        ConfigService configService,
        CacheService cacheService,
        IBackendService backendService) : base(
        PageName.Task, "\uE1BC")
    {
        ControlPanelViewModel = controlPanelViewModel;
        _commonModel = commonModel;
        _configService = configService;
        _cacheService = cacheService;
        _backendService = backendService;
        CurrentConfig = _configService.TasksConfig!;

        _cacheService.Cache.PropertyChanged += OnCachePropertyChanged;

        if (Cache.Strategies.Count == 0) _ = RefreshStrategies();
        return;

        void OnCachePropertyChanged(object? _, PropertyChangedEventArgs args)
        {
            if (args.PropertyName != nameof(Cache.CurrentConfigIndex)) return;
            _configService.SwitchConfig(_cacheService.Cache.ConfigNames[_cacheService.Cache.CurrentConfigIndex]);
            CurrentConfig = _configService.TasksConfig!;
        }
    }

    public string[] TpTaskNames => [.. _tpTasks.Select(t => t.Name)];
    public TpTaskLevel[] CurrentTpTaskLevels => _tpTasks.ElementAt(SelectedTpTaskIndex).Levels;
    public string[] GardenOfPlentyLevels1 => [.. _tpTasks.ElementAt(1).Levels.Select(x => $"{x.Name}（{x.Result}）")];
    public string[] GardenOfPlentyLevels2 => [.. _tpTasks.ElementAt(2).Levels.Select(x => $"{x.Name}（{x.Result}）")];
    public string[] PlanarFissureLevels => [.. _tpTasks.ElementAt(0).Levels.Select(x => $"{x.Name}（{x.Result}）")];
    public string[] RealmOfTheStrangeLevels => [.. _tpTasks.ElementAt(4).Levels.Select(x => $"{x.Name}（{x.Result}）")];
    public int CurrentTpTaskMaxSingleTimes => _tpTasks[SelectedTpTaskIndex].MaxSingleTimes;
    
    public string TaskListText =>
        TrailblazePowerConfig.TaskList.Count == 0
            ? "暂无任务"
            : $"{string.Join("、", TrailblazePowerConfig.TaskList.Select(x => x.Name).Take(3))} 等 {TrailblazePowerConfig.TaskList.Count} 个任务";
    public CosmicStrifeConfig CosmicStrifeConfig => CurrentConfig.CosmicStrife;
    public MissionAccomplishedConfig MissionAccomplishedConfig => CurrentConfig.MissionAccomplished;
    public ReceiveRewardsConfig ReceiveRewardsConfig => CurrentConfig.ReceiveRewards;
    public StartGameConfig StartGameConfig => CurrentConfig.StartGame;
    public TrailblazePowerConfig TrailblazePowerConfig => CurrentConfig.TrailblazePower;

    public int CurrencyWarsStrategyIndex
    {
        get => CosmicStrifeConfig.CurrencyWarsStrategyIndex;
        set
        {
            CosmicStrifeConfig.CurrencyWarsStrategyIndex = value;
            OnPropertyChanged();
            CosmicStrifeConfig.CurrencyWarsStrategy = Cache.Strategies.ElementAtOrDefault(value)?.FileName ?? "";
        }
    }

    public ControlPanelViewModel ControlPanelViewModel { get; }

    public TopLevel? TopLevelObject { get; set; }

    public bool EnableContextMenu => SelectedTaskItem is not null;

    public int CurrencyWarsModeIndex
    {
        get => CosmicStrifeConfig.CurrencyWarsMode;
        set
        {
            CosmicStrifeConfig.CurrencyWarsMode = value;
            OnPropertyChanged(nameof(IsCwNormalMode));
        }
    }

    public bool IsCwNormalMode => CosmicStrifeConfig.CurrencyWarsMode != 2;

    public Cache Cache => _cacheService.Cache;

    public async Task GetTpConfigAsync()
    {
        if (_tpTasks.Length > 0) return;
        _tpTasks = await _backendService.GetTpConfigAsync();
        OnPropertyChanged(nameof(TpTaskNames));
        OnPropertyChanged(nameof(CurrentTpTaskLevels));
        OnPropertyChanged(nameof(GardenOfPlentyLevels1));
        OnPropertyChanged(nameof(GardenOfPlentyLevels2));
        OnPropertyChanged(nameof(PlanarFissureLevels));
        OnPropertyChanged(nameof(RealmOfTheStrangeLevels));
        OnPropertyChanged(nameof(CurrentTpTaskMaxSingleTimes));
    }

    [RelayCommand]
    private async Task SingleTask(string taskName)
    {
        await ControlPanelViewModel.StartSingleTask(taskName);
    }

    [RelayCommand]
    private async Task RefreshStrategies()
    {
        try
        {
            var strategies = await _backendService.GetStrategiesAsync();
            Cache.Strategies.Clear();
            foreach (var strategy in strategies)
                Cache.Strategies.Add(strategy);
            CurrencyWarsStrategyIndex = 0;
        }
        catch (Exception ex)
        {
            _commonModel.ShowErrorToast("攻略加载失败", ex.Message);
        }
    }

    [RelayCommand]
    private async Task SelectedPath()
    {
        if (TopLevelObject is null) return;
        var files = await TopLevelObject.StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions());
        if (files.Count == 0) return;
        StartGameConfig.GamePath = files[0].Path.LocalPath;
    }

    [RelayCommand]
    private void DeleteSelectedTaskItem()
    {
        if (SelectedTaskItem is TrailblazePowerTaskItem item) TrailblazePowerConfig.TaskList.Remove(item);
    }

    [RelayCommand]
    private void AddTaskItem()
    {
        if (SelectedTpTaskLevel is null)
        {
            _commonModel.ShowInfoToast("Info", "请选择副本关卡后再添加任务");
            return;
        }

        TrailblazePowerConfig.TaskList.Add(new TrailblazePowerTaskItem
        {
            Name = _tpTasks[SelectedTpTaskIndex].Name,
            Id = _tpTasks[SelectedTpTaskIndex].Id,
            Level = SelectedTpTaskLevel.Id,
            LevelName = SelectedTpTaskLevel.Name,
            Count = TpTaskSingleTimes,
            RunTimes = TpTaskRunTimes,
            AutoDetect = IsTpTaskAutoDetect
        });
    }

    [RelayCommand]
    private async Task ShowTaskListControl()
    {
        var taskListControl = new TpTaskListControl
        {
            DataContext = this
        };
        await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Content = taskListControl
        });
        OnPropertyChanged(nameof(TaskListText));  // 窗口关闭时更新显示文本
    }

    [RelayCommand]
    private void ShowAddTaskControl()
    {
        var addTaskControl = new TpAddTaskControl
        {
            DataContext = this
        };
        SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Content = addTaskControl
        });
    }
}

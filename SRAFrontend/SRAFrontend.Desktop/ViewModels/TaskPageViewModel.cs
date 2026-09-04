using System;
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
    private partial TasksConfig CurrentConfig { get; set; }

    [ObservableProperty]
    public partial bool IsTpTaskAutoDetect { get; set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(EnableContextMenu))]
    public partial object? SelectedTaskItem { get; set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(CurrentTpTaskLevels), nameof(CurrentTpTaskMaxSingleTimes))]
    public partial int SelectedTpTaskIndex { get; set; }

    public int SelectedGardenOfPlentyLevels1Index
    {
        get => TrailblazePowerConfig.GardenOfPlentyLevel1;
        set
        {
            TrailblazePowerConfig.GardenOfPlentyLevel1 = value;
            OnPropertyChanged();
        }
    }
    public int SelectedGardenOfPlentyLevels2Index
    {
        get => TrailblazePowerConfig.GardenOfPlentyLevel2;
        set
        {
            TrailblazePowerConfig.GardenOfPlentyLevel2 = value;
            OnPropertyChanged();
        }
    }

    public int SelectedPlanarFissureLevelsIndex
    {
        get => TrailblazePowerConfig.PlanarFissureLevel;
        set
        {
            TrailblazePowerConfig.PlanarFissureLevel = value;
            OnPropertyChanged();
        }
    }

    public int SelectedRealmOfTheStrangeLevelsIndex
    {
        get => TrailblazePowerConfig.RealmOfTheStrangeLevel;
        set
        {
            TrailblazePowerConfig.RealmOfTheStrangeLevel = value;
            OnPropertyChanged();
        }
    }

    [ObservableProperty]
    public partial TpTaskLevel? SelectedTpTaskLevel { get; set; }

    [ObservableProperty]
    public partial int TpTaskRunTimes { get; set; } = 1;

    [ObservableProperty]
    public partial int TpTaskSingleTimes { get; set; } = 1;

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
    public string[] GardenOfPlentyLevels1 => ["未选择", .. _tpTasks.ElementAt(1).Levels.Select(x => $"{x.Name}（{x.Result}）")];
    public string[] GardenOfPlentyLevels2 => ["未选择", .. _tpTasks.ElementAt(2).Levels.Select(x => $"{x.Name}（{x.Result}）")];
    public string[] PlanarFissureLevels => ["未选择", .. _tpTasks.ElementAt(0).Levels.Select(x => $"{x.Name}（{x.Result}）")];
    public string[] RealmOfTheStrangeLevels => ["未选择", .. _tpTasks.ElementAt(4).Levels.Select(x => $"{x.Name}（{x.Result}）")];
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
    private async Task ShowAddTaskControl()
    {
        var result = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Content = new TpAddTaskControl{DataContext = this},
            ActionButtonsPreset = SukiMessageBoxButtons.ApplyCancel
        });
        if (result is SukiMessageBoxResult.Apply)
        {
            AddTaskItem();
        }
    }
    
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
}

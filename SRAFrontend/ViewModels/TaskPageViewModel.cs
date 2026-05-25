using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Platform.Storage;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Controls;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SukiUI.Controls;
using SukiUI.MessageBox;

namespace SRAFrontend.ViewModels;

public partial class TaskPageViewModel : PageViewModel
{
    private readonly CacheService _cacheService;
    private readonly CommonModel _commonModel;
    private readonly ConfigService _configService;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(CosmicStrifeConfig), nameof(MissionAccomplishedConfig),
        nameof(ReceiveRewardsConfig), nameof(StartGameConfig), nameof(TrailblazePowerConfig))]
    private TasksConfig _currentConfig;

    [ObservableProperty] private bool _isTpTaskAutoDetect;

    [ObservableProperty] [NotifyPropertyChangedFor(nameof(EnableContextMenu))]
    private object? _selectedTaskItem;

    [ObservableProperty] [NotifyPropertyChangedFor(nameof(CurrentTpTaskLevels), nameof(CurrentTpTaskMaxSingleTimes))]
    private int _selectedTpTaskIndex;

    [ObservableProperty] private int _selectedTpTaskLevelIndex;

    [ObservableProperty] private int _tpTaskRunTimes = 1;

    [ObservableProperty] private int _tpTaskSingleTimes = 1;

    public TaskPageViewModel(
        CommonModel commonModel,
        ControlPanelViewModel controlPanelViewModel,
        ConfigService configService,
        CacheService cacheService) : base(
        PageName.Task, "\uE1BC")
    {
        ControlPanelViewModel = controlPanelViewModel;
        _commonModel = commonModel;
        _configService = configService;
        _cacheService = cacheService;
        CurrentConfig = _configService.TaskConfig!;

        void OnCachePropertyChanged(object? _, PropertyChangedEventArgs args)
        {
            if (args.PropertyName != nameof(Cache.CurrentConfigIndex)) return;
            _configService.SwitchConfig(_cacheService.Cache.ConfigNames[_cacheService.Cache.CurrentConfigIndex]);
            CurrentConfig = _configService.TaskConfig!;
        }

        _cacheService.Cache.PropertyChanged += OnCachePropertyChanged;

        if (Cache.Strategies.Count == 0) RefreshStrategies();
    }

    public string[] TpTaskNames => TpTaskItems.TpTaskNames;
    public string[] CurrentTpTaskLevels => TpTaskItems.GetLevelsByIndex(SelectedTpTaskIndex);
    public string[] GardenOfPlentyLevels1 => TpTaskItems.GetLevelsByIndex(1);
    public string[] GardenOfPlentyLevels2 => TpTaskItems.GetLevelsByIndex(2);
    public string[] PlanarFissureLevels => TpTaskItems.GetLevelsByIndex(0);
    public string[] RealmOfTheStrangeLevels => TpTaskItems.GetLevelsByIndex(4);
    public int CurrentTpTaskMaxSingleTimes => TpTaskItems.GetMaxSingleTimesByIndex(SelectedTpTaskIndex);
    
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

    [RelayCommand]
    private void SingleTask(string taskName)
    {
        ControlPanelViewModel.StartSingleTask(taskName);
    }

    [RelayCommand]    private void RefreshStrategies()
    {
        if (!Directory.Exists(PathString.StrategiesDir))
        {
            _commonModel.ShowErrorToast("Error", "未找到攻略文件夹，无法刷新");
            return;
        }

        // 遍历攻略文件夹中的json文件，反序列化成Strategy对象，并更新Cache中的Strategies列表
        var strategies = new List<Strategy>();
        foreach (var file in Directory.GetFiles(PathString.StrategiesDir))
        {
            if (!file.EndsWith(".json")) continue;
            var json = File.ReadAllText(file);
            try
            {
                var strategy = JsonSerializer.Deserialize<Strategy>(json);
                if (strategy is null) continue;
                strategy.FileName = Path.GetFileNameWithoutExtension(file);
                strategies.Add(strategy);
            }
            catch (JsonException ex)
            {
                _commonModel.ShowErrorToast("攻略加载失败", $"文件 {Path.GetFileName(file)} 格式错误：{ex.Message}");
            }
        }

        Cache.Strategies.Clear();
        Cache.Strategies.AddRange(strategies);
        CurrencyWarsStrategyIndex = 0;
    }

        // 遍历攻略文件夹中的json文件，反序列化成Strategy对象，并更新Cache中的Strategies列表
        var strategies = new List<Strategy>();
        foreach (var file in Directory.GetFiles(PathString.StrategiesDir))
        {
            if (!file.EndsWith(".json")) continue;
            var json = File.ReadAllText(file);
            var strategy = JsonSerializer.Deserialize<Strategy>(json);
            if (strategy is null) continue;
            strategy.FileName = Path.GetFileNameWithoutExtension(file);
            strategies.Add(strategy);
        }

        Cache.Strategies.Clear();
        Cache.Strategies.AddRange(strategies);
        CurrencyWarsStrategyIndex = 0;
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
        if (SelectedTpTaskLevelIndex == 0)
        {
            _commonModel.ShowInfoToast("Info", "请选择副本关卡后再添加任务");
            return;
        }

        TrailblazePowerConfig.TaskList.Add(new TrailblazePowerTaskItem
        {
            Name = TpTaskItems.TpTaskNames[SelectedTpTaskIndex],
            Id = TpTaskItems.TaskItems[SelectedTpTaskIndex].Id,
            Level = SelectedTpTaskLevelIndex,
            LevelName = CurrentTpTaskLevels.ElementAtOrDefault(SelectedTpTaskLevelIndex) ?? "",
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
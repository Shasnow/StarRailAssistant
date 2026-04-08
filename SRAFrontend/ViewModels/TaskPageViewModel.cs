using System;
using System.Collections.Generic;
using Avalonia.Data.Converters;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia.Collections;
using Avalonia.Controls;
using Avalonia.Platform.Storage;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Controls;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;



/// <summary>任务排序列表项，绑定到拖拽列表</summary>
public partial class TaskOrderItem : ObservableObject
{
    [ObservableProperty] private bool _isEnabled;
    [ObservableProperty] private bool _isSelected;
    public string ClassName { get; set; } = "";
    public string DisplayName { get; set; } = "";
    /// <summary>固定位置，不可移动（启动游戏固定首位，任务完成固定末位）</summary>
    public bool IsFixed { get; set; } = false;
    public bool IsMovable => !IsFixed;
    /// <summary>在 AllTaskDefs 中的原始索引（用于 EnabledTasks 绑定）</summary>
    public int OriginalIndex { get; set; } = -1;
}

public partial class TaskPageViewModel : PageViewModel
{
    private readonly CacheService _cacheService;
    private readonly ConfigService _configService;
    private readonly CommonModel _commonModel;

    [ObservableProperty] private Config _currentConfig;

    [ObservableProperty] private AvaloniaList<TaskOrderItem> _taskOrderList = [];

    [ObservableProperty] [NotifyPropertyChangedFor(nameof(EnableContextMenu))]
    private object? _selectedTaskItem;

    public int CurrencyWarsStrategyIndex
    {
        get => CurrentConfig.CurrencyWarsStrategyIndex;
        set
        {
            CurrentConfig.CurrencyWarsStrategyIndex = value;
            OnPropertyChanged();
            CurrentConfig.CurrencyWarsStrategy = Cache.Strategies.ElementAtOrDefault(value)?.FileName ?? "";
        }
    }

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
        CurrentConfig = _configService.Config!;

        void OnCachePropertyChanged(object? _, PropertyChangedEventArgs args)
        {
            if (args.PropertyName != nameof(Cache.CurrentConfigIndex)) return;
            _configService.SwitchConfig(_cacheService.Cache.ConfigNames[_cacheService.Cache.CurrentConfigIndex]);
            CurrentConfig = _configService.Config!;
            InitTaskOrderList();
        }

        _cacheService.Cache.PropertyChanged += OnCachePropertyChanged;

        if (Cache.Strategies.Count == 0)
        {
            RefreshStrategies();
        }
        InitTaskOrderList();
    }

    // 固定在首位/末位的任务类名
    private static readonly string FixedFirstTask = "StartGameTask";
    private static readonly string FixedLastTask  = "MissionAccomplishTask";

    // 所有任务的静态定义（类名 -> 显示名）
    private static readonly List<(string ClassName, string DisplayName)> AllTaskDefs =
    [
        ("StartGameTask",         "启动游戏"),
        ("TrailblazePowerTask",   "清开拓力"),
        ("ReceiveRewardsTask",    "领取奖励"),
        ("CosmicStrifeTask",      "旷宇纷争"),
        ("MissionAccomplishTask", "任务完成"),
    ];

    /// <summary>从 Config 初始化任务排序列表</summary>
    private void InitTaskOrderList()
    {
        TaskOrderList.Clear();

        // 构建中间任务的有序列表（排除首尾固定任务）
        var middleDefs = AllTaskDefs.Where(d => d.ClassName != FixedFirstTask && d.ClassName != FixedLastTask).ToList();
        var firstDef = AllTaskDefs.First(d => d.ClassName == FixedFirstTask);
        var lastDef  = AllTaskDefs.First(d => d.ClassName == FixedLastTask);

        List<(string ClassName, string DisplayName, bool Enabled)> middleItems;

        if (CurrentConfig.TaskOrder.Count > 0)
        {
            // 新格式：从 TaskOrder 里提取中间任务的顺序和启用状态
            var orderMap = new Dictionary<string, int>();
            for (int i = 0; i < CurrentConfig.TaskOrder.Count; i++)
                orderMap[CurrentConfig.TaskOrder[i]] = i;

            var enabledMiddle = CurrentConfig.TaskOrder
                .Where(c => c != FixedFirstTask && c != FixedLastTask)
                .Select(c => (c, AllTaskDefs.FirstOrDefault(d => d.ClassName == c).DisplayName, true))
                .Where(t => !string.IsNullOrEmpty(t.DisplayName))
                .ToList();

            var enabledSet = new HashSet<string>(enabledMiddle.Select(t => t.c));
            var disabledMiddle = middleDefs
                .Where(d => !enabledSet.Contains(d.ClassName))
                .Select(d => (d.ClassName, d.DisplayName, false))
                .ToList();

            middleItems = enabledMiddle.Concat(disabledMiddle).ToList();
        }
        else
        {
            // 旧格式迁移：EnabledTasks bool 数组
            middleItems = middleDefs.Select((d, i) =>
            {
                int origIdx = AllTaskDefs.FindIndex(x => x.ClassName == d.ClassName);
                bool enabled = origIdx >= 0 && origIdx < CurrentConfig.EnabledTasks.Length && CurrentConfig.EnabledTasks[origIdx];
                return (d.ClassName, d.DisplayName, enabled);
            }).ToList();
        }

        // 首位固定任务（启动游戏）
        bool firstEnabled = CurrentConfig.TaskOrder.Count > 0
            ? CurrentConfig.TaskOrder.Contains(FixedFirstTask)
            : (0 < CurrentConfig.EnabledTasks.Length && CurrentConfig.EnabledTasks[0]);
        TaskOrderList.Add(new TaskOrderItem { ClassName = firstDef.ClassName, DisplayName = firstDef.DisplayName, IsEnabled = firstEnabled, IsFixed = true, OriginalIndex = AllTaskDefs.FindIndex(d => d.ClassName == firstDef.ClassName) });

        // 中间可移动任务
        foreach (var (className, displayName, enabled) in middleItems)
            TaskOrderList.Add(new TaskOrderItem { ClassName = className, DisplayName = displayName, IsEnabled = enabled, IsFixed = false, OriginalIndex = AllTaskDefs.FindIndex(d => d.ClassName == className) });

        // 末位固定任务（任务完成）
        bool lastEnabled = CurrentConfig.TaskOrder.Count > 0
            ? CurrentConfig.TaskOrder.Contains(FixedLastTask)
            : (4 < CurrentConfig.EnabledTasks.Length && CurrentConfig.EnabledTasks[4]);
        TaskOrderList.Add(new TaskOrderItem { ClassName = lastDef.ClassName, DisplayName = lastDef.DisplayName, IsEnabled = lastEnabled, IsFixed = true, OriginalIndex = AllTaskDefs.FindIndex(d => d.ClassName == lastDef.ClassName) });

        // 监听每个 item 的 IsEnabled 变化，同步回 Config.TaskOrder
        foreach (var item in TaskOrderList)
            item.PropertyChanged += (_, _) => SyncTaskOrderToConfig();

        // 初始化完成后立即同步一次，确保 TaskOrder 包含全部任务顺序
        SyncTaskOrderToConfig();

        // 初始化时通知一次
        OnPropertyChanged(nameof(StartGameTaskEnabled));
        OnPropertyChanged(nameof(TrailblazePowerTaskEnabled));
        OnPropertyChanged(nameof(ReceiveRewardsTaskEnabled));
        OnPropertyChanged(nameof(CosmicStrifeTaskEnabled));
        OnPropertyChanged(nameof(MissionAccomplishTaskEnabled));

        // 默认选中第一个任务
        if (TaskOrderList.Count > 0)
            SelectTask(TaskOrderList[0].ClassName);
    }

    /// <summary>根据 ClassName 获取 TaskOrderItem（供各 TaskView 绑定使用）</summary>
    public TaskOrderItem? GetTaskItem(string className)
        => TaskOrderList.FirstOrDefault(t => t.ClassName == className);

    // 当前选中的任务 ClassName
    private string _selectedClassName = "StartGameTask";

    /// <summary>选中指定任务，更新 IsSelected 状态</summary>
    public void SelectTask(string className)
    {
        _selectedClassName = className;
        foreach (var item in TaskOrderList)
            item.IsSelected = item.ClassName == className;
        OnPropertyChanged(nameof(StartGameTaskSelected));
        OnPropertyChanged(nameof(TrailblazePowerTaskSelected));
        OnPropertyChanged(nameof(ReceiveRewardsTaskSelected));
        OnPropertyChanged(nameof(CosmicStrifeTaskSelected));
        OnPropertyChanged(nameof(MissionAccomplishTaskSelected));
    }

    // 各任务内容区域的显示控制
    public bool StartGameTaskSelected         => _selectedClassName == "StartGameTask";
    public bool TrailblazePowerTaskSelected   => _selectedClassName == "TrailblazePowerTask";
    public bool ReceiveRewardsTaskSelected    => _selectedClassName == "ReceiveRewardsTask";
    public bool CosmicStrifeTaskSelected      => _selectedClassName == "CosmicStrifeTask";
    public bool MissionAccomplishTaskSelected => _selectedClassName == "MissionAccomplishTask";

    // 各任务启用状态属性（供 TaskView 绑定，替代 EnabledTasks[n]）
    public bool StartGameTaskEnabled
    {
        get => GetTaskItem("StartGameTask")?.IsEnabled ?? false;
        set { var t = GetTaskItem("StartGameTask"); if (t != null) t.IsEnabled = value; }
    }
    public bool TrailblazePowerTaskEnabled
    {
        get => GetTaskItem("TrailblazePowerTask")?.IsEnabled ?? false;
        set { var t = GetTaskItem("TrailblazePowerTask"); if (t != null) t.IsEnabled = value; }
    }
    public bool ReceiveRewardsTaskEnabled
    {
        get => GetTaskItem("ReceiveRewardsTask")?.IsEnabled ?? false;
        set { var t = GetTaskItem("ReceiveRewardsTask"); if (t != null) t.IsEnabled = value; }
    }
    public bool CosmicStrifeTaskEnabled
    {
        get => GetTaskItem("CosmicStrifeTask")?.IsEnabled ?? false;
        set { var t = GetTaskItem("CosmicStrifeTask"); if (t != null) t.IsEnabled = value; }
    }
    public bool MissionAccomplishTaskEnabled
    {
        get => GetTaskItem("MissionAccomplishTask")?.IsEnabled ?? false;
        set { var t = GetTaskItem("MissionAccomplishTask"); if (t != null) t.IsEnabled = value; }
    }

    /// <summary>把当前列表状态同步回 Config.TaskOrder</summary>
    private void SyncTaskOrderToConfig()
    {
        // TaskOrder 保存所有任务的顺序（不过滤启用状态）
        // EnabledTasks 继续负责启用状态，由各 TaskView 的 CheckBox 直接绑定
        CurrentConfig.TaskOrder.Clear();
        foreach (var item in TaskOrderList)
            CurrentConfig.TaskOrder.Add(item.ClassName);
        // 通知各任务 IsEnabled 属性变化
        OnPropertyChanged(nameof(StartGameTaskEnabled));
        OnPropertyChanged(nameof(TrailblazePowerTaskEnabled));
        OnPropertyChanged(nameof(ReceiveRewardsTaskEnabled));
        OnPropertyChanged(nameof(CosmicStrifeTaskEnabled));
        OnPropertyChanged(nameof(MissionAccomplishTaskEnabled));
    }

    [RelayCommand]
    private void MoveTaskUp(TaskOrderItem item)
    {
        if (item.IsFixed) return;
        var idx = TaskOrderList.IndexOf(item);
        if (idx <= 0) return;
        // 不能移到固定首位任务之前
        var prev = TaskOrderList[idx - 1];
        if (prev.IsFixed) return;
        TaskOrderList.RemoveAt(idx);
        TaskOrderList.Insert(idx - 1, item);
        item.PropertyChanged += (_, _) => SyncTaskOrderToConfig();
        SyncTaskOrderToConfig();
    }

    [RelayCommand]
    private void MoveTaskDown(TaskOrderItem item)
    {
        if (item.IsFixed) return;
        var idx = TaskOrderList.IndexOf(item);
        if (idx < 0 || idx >= TaskOrderList.Count - 1) return;
        // 不能移到固定末位任务之后
        var next = TaskOrderList[idx + 1];
        if (next.IsFixed) return;
        TaskOrderList.RemoveAt(idx);
        TaskOrderList.Insert(idx + 1, item);
        item.PropertyChanged += (_, _) => SyncTaskOrderToConfig();
        SyncTaskOrderToConfig();
    }

    /// <summary>拖拽时直接移动到指定索引位置</summary>
    public void MoveTaskToIndex(TaskOrderItem item, int targetIndex)
    {
        if (item.IsFixed) return;
        var idx = TaskOrderList.IndexOf(item);
        if (idx < 0 || idx == targetIndex) return;
        if (targetIndex < 0 || targetIndex >= TaskOrderList.Count) return;
        // 不能越过固定任务的边界
        var target = TaskOrderList[targetIndex];
        if (target.IsFixed) return;
        TaskOrderList.RemoveAt(idx);
        TaskOrderList.Insert(targetIndex, item);
        item.PropertyChanged += (_, _) => SyncTaskOrderToConfig();
        SyncTaskOrderToConfig();
    }

    public ControlPanelViewModel ControlPanelViewModel { get; }

    public AvaloniaList<TrailblazePowerTask> Tasks => [
            new(AddTaskItem)
            {
                Title = "饰品提取",
                Id = "ornament_extraction",
                Cost = 40,
                Levels = new[]
                {
                    "---选择副本---",
                    "鎏金追忆（朋克洛德/千星城）",
                    "西风丛中（翁法罗斯/天国@直播间）",
                    "月下朱殷（妖精/海隅）",
                    "纷争不休（拾骨地/巨树）",
                    "蠹役饥肠（露莎卡/蕉乐园）",
                    "永恒笑剧（都蓝/劫火）",
                    "伴你入眠（茨冈尼亚/出云显世）",
                    "天剑如雨（格拉默/匹诺康尼）",
                    "孽果盘生（繁星/龙骨）",
                    "百年冻土（贝洛伯格/萨尔索图）",
                    "温柔话语（公司/差分机）",
                    "浴火钢心（塔利亚/翁瓦克）",
                    "坚城不倒（太空封印站/仙舟）"
                },
                MaxSingleTimes = 6
            },

            new(AddTaskItem)
            {
                Title = "拟造花萼（金）",
                Id = "calyx_golden",
                Cost = 10,
                Levels = new[]
                {
                    "---选择副本---",
                    "回忆之蕾（二相乐园）",
                    "以太之蕾（二相乐园）",
                    "珍藏之蕾（二相乐园）",
                    "回忆之蕾（翁法罗斯）",
                    "以太之蕾（翁法罗斯）",
                    "珍藏之蕾（翁法罗斯）",
                    "回忆之蕾（匹诺康尼）",
                    "以太之蕾（匹诺康尼）",
                    "珍藏之蕾（匹诺康尼）",
                    "回忆之蕾（仙舟罗浮）",
                    "以太之蕾（仙舟罗浮）",
                    "珍藏之蕾（仙舟罗浮）",
                    "回忆之蕾（雅利洛VI）",
                    "以太之蕾（雅利洛VI）",
                    "珍藏之蕾（雅利洛VI）"
                },
                MaxSingleTimes = 24
            },

            new(AddTaskItem)
            {
                Title = "拟造花萼（赤）",
                Id = "calyx_crimson",
                Cost = 10,
                Levels = new[]
                {
                    "---选择副本---",
                    "月狂獠牙（毁灭）",
                    "净世残刃（毀灭）",
                    "神体琥珀（存护）",
                    "琥珀的坚守（存护）",
                    "天谴血矛（巡猎）",
                    "逆时一击（巡猎）",
                    "逐星之矢（巡猎）",
                    "万象果实（丰饶）",
                    "永恒之花（丰饶）",
                    "精致色稿（智识）",
                    "智识之钥（智识）",
                    "天外乐章（同谐）",
                    "群星乐章（同谐）",
                    "焚天之魔（虚无）",
                    "沉沦黑曜（虚无）",
                    "阿赖耶华（记忆）",
                    "《绒绒号》典藏版合集（欢愉）"
                },
                MaxSingleTimes = 24
            },

            new(AddTaskItem)
            {
                Title = "凝滞虚影",
                Id = "stagnant_shadow",
                Cost = 30,
                Levels = new[]
                {
                    "---选择副本---",
                    "侵略凝块（物理）",
                    "星际和平工作证（物理）",
                    "幽府通令（物理）",
                    "铁狼碎齿（物理）",
                    "明辉日珥（火）",
                    "忿火之心（火）",
                    "过热钢刀（火）",
                    "恒温晶壳（火）",
                    "海妖残鰭（冰）",
                    "冷藏梦箱（冰）",
                    "苦寒晶壳（冰）",
                    "风雪之角（冰）",
                    "狂雷扫弦（雷）",
                    "兽馆之钉（雷）",
                    "炼形者雷枝（雷）",
                    "往日之影的雷冠（雷）",
                    "暮辉烬蕾（风）",
                    "一杯酪酊的时代（风）",
                    "无人遗垢（风）",
                    "暴风之眼（风）",
                    "暗帷月华（量子）",
                    "炙梦喷枪（量子）",
                    "苍猿之钉（量子）",
                    "虚幻铸铁（量子）",
                    "纷争前兆（虚数）",
                    "一曲和弦的幻景（虚数）",
                    "镇灵敕符（虚数）",
                    "往日之影的金饰（虚数）"
                },
                MaxSingleTimes = 8
            },

            new(AddTaskItem)
            {
                Title = "侵蚀隧洞",
                Id = "caver_of_corrosion",
                Cost = 40,
                Levels = new[]
                {
                    "---选择副本---",
                    "魔占之径（魔法少女/卜者）",
                    "隐救之径（救世主/隐士）",
                    "雳勇之径（女武神/船长）",
                    "弦歌之径（英豪/诗人）",
                    "迷识之径（司铎套/学者套）",
                    "勇骑之径（铁骑套/勇烈套）",
                    "梦潜之径（死水/钟表匠）",
                    "幽冥之径（大公/幽囚）",
                    "药使之径（莳者/信使）",
                    "野焰之径（火匠/废土客）",
                    "圣颂之径（圣骑/乐队）",
                    "睿智之径（铁卫/量子套）",
                    "漂泊之径（过客/快枪手）",
                    "迅拳之径（拳皇/怪盗）",
                    "霜风之径（冰/风套）"
                },
                MaxSingleTimes = 6
            },

            new(AddTaskItem)
            {
                Title = "历战余响",
                Id = "echo_of_war",
                Cost = 30,
                Levels = new[]
                {
                    "---选择副本---",
                    "铁骸的锈冢",
                    "晨昏的回眸",
                    "心兽的战场",
                    "尘梦的赞礼",
                    "蛀星的旧靥",
                    "不死的神实",
                    "寒潮的落幕",
                    "毁灭的开端"
                },
                MaxSingleTimes = 3,
                CanAutoDetect = false
            }
        ];

    public TopLevel? TopLevelObject { get; set; }

    public bool EnableContextMenu => SelectedTaskItem is not null;

    public int CurrencyWarsModeIndex
    {
        get => CurrentConfig.CurrencyWarsMode;
        set
        {
            CurrentConfig.CurrencyWarsMode = value;
            OnPropertyChanged(nameof(IsCwNormalMode));
        }
    }

    public bool IsCwNormalMode => CurrentConfig.CurrencyWarsMode != 2;

    public Cache Cache => _cacheService.Cache;

    [RelayCommand]
    private void SingleTask(string taskName)
    {
        ControlPanelViewModel.StartSingleTask(taskName);
    }

    [RelayCommand]
    private void RefreshStrategies()
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
        CurrentConfig.StartGamePath = files[0].Path.LocalPath;
    }

    [RelayCommand]
    private void DeleteSelectedTaskItem()
    {
        if (SelectedTaskItem is TrailblazePowerTaskItem item) CurrentConfig.TrailblazePowerTaskList.Remove(item);
    }

    private void AddTaskItem(TrailblazePowerTask task)
    {
        if (task.SelectedIndex == 0)
        {
            _commonModel.ShowInfoToast("Info", "请选择副本关卡后再添加任务");
            return;
        }

        CurrentConfig.TrailblazePowerTaskList.Add(new TrailblazePowerTaskItem
        {
            Name = task.Title,
            Id = task.Id,
            Level = task.SelectedIndex,
            LevelName = (task.Levels?.Cast<string>()!).ElementAtOrDefault(task.SelectedIndex) ?? string.Empty,
            Count = task.Count,
            RunTimes = task.RunTimes,
            AutoDetect = task.IsAutoDetect
        });
    }
}
using System.Collections.Generic;
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

public partial class TaskPageViewModel : PageViewModel
{
    private readonly CacheService _cacheService;
    private readonly ConfigService _configService;
    private readonly CommonModel _commonModel;
    private readonly SraService _sraService;

    [ObservableProperty] private Config _currentConfig;

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
        CacheService cacheService,
        SraService sraService) : base(
        PageName.Task, "\uE1BC")
    {
        ControlPanelViewModel = controlPanelViewModel;
        _commonModel = commonModel;
        _configService = configService;
        _cacheService = cacheService;
        _sraService = sraService;
        CurrentConfig = _configService.Config!;

        void OnCachePropertyChanged(object? _, PropertyChangedEventArgs args)
        {
            if (args.PropertyName != nameof(Cache.CurrentConfigIndex)) return;
            _configService.SwitchConfig(_cacheService.Cache.ConfigNames[_cacheService.Cache.CurrentConfigIndex]);
            CurrentConfig = _configService.Config!;
            // 刷新任务启用状态绑定
            OnPropertyChanged(nameof(IsStartGameEnabled));
            OnPropertyChanged(nameof(IsTrailblazePowerEnabled));
            OnPropertyChanged(nameof(IsReceiveRewardsEnabled));
            OnPropertyChanged(nameof(IsCosmicStrifeEnabled));
            OnPropertyChanged(nameof(IsMissionAccomplishEnabled));
            RefreshTaskOrderItems();
        }

        _cacheService.Cache.PropertyChanged += OnCachePropertyChanged;

        if (Cache.Strategies.Count == 0)
        {
            RefreshStrategies();
        }

        RefreshTaskOrderItems();
    }

    public ControlPanelViewModel ControlPanelViewModel { get; }

    // ============================================================
    // 任务启用状态计算属性（供 XAML CheckBox 绑定）
    // ============================================================

    public bool IsStartGameEnabled
    {
        get => CurrentConfig.IsTaskEnabled("StartGameTask");
        set { CurrentConfig.SetTaskEnabled("StartGameTask", value); OnPropertyChanged(); RefreshTaskOrderItems(); }
    }

    public bool IsTrailblazePowerEnabled
    {
        get => CurrentConfig.IsTaskEnabled("TrailblazePowerTask");
        set { CurrentConfig.SetTaskEnabled("TrailblazePowerTask", value); OnPropertyChanged(); RefreshTaskOrderItems(); }
    }

    public bool IsReceiveRewardsEnabled
    {
        get => CurrentConfig.IsTaskEnabled("ReceiveRewardsTask");
        set { CurrentConfig.SetTaskEnabled("ReceiveRewardsTask", value); OnPropertyChanged(); RefreshTaskOrderItems(); }
    }

    public bool IsCosmicStrifeEnabled
    {
        get => CurrentConfig.IsTaskEnabled("CosmicStrifeTask");
        set { CurrentConfig.SetTaskEnabled("CosmicStrifeTask", value); OnPropertyChanged(); RefreshTaskOrderItems(); }
    }

    public bool IsMissionAccomplishEnabled
    {
        get => CurrentConfig.IsTaskEnabled("MissionAccomplishTask");
        set { CurrentConfig.SetTaskEnabled("MissionAccomplishTask", value); OnPropertyChanged(); RefreshTaskOrderItems(); }
    }

    // ============================================================
    // 任务排序面板
    // ============================================================

    /// <summary>固定位置任务集合</summary>
    private static readonly HashSet<string> FixedTasks = new() { "StartGameTask", "MissionAccomplishTask" };

    // 各非 fixed 任务的可移动状态（供 XAML 绑定）
    [ObservableProperty] private bool _isTrailblazePowerCanMoveLeft;
    [ObservableProperty] private bool _isTrailblazePowerCanMoveRight;
    [ObservableProperty] private bool _isReceiveRewardsCanMoveLeft;
    [ObservableProperty] private bool _isReceiveRewardsCanMoveRight;
    [ObservableProperty] private bool _isCosmicStrifeCanMoveLeft;
    [ObservableProperty] private bool _isCosmicStrifeCanMoveRight;

    /// <summary>按 TaskOrder 排列的 Tab 标题列表（供 TabControl 动态排序）</summary>
    [ObservableProperty] private AvaloniaList<string> _orderedTabKeys = [];

    /// <summary>根据 CurrentConfig.TaskOrder 刷新排序面板</summary>
    private void RefreshTaskOrderItems()
    {
        var order = CurrentConfig.TaskOrder;

        // 刷新 Tab 顺序：fixed 任务钉在首尾，非 fixed 任务按 TaskOrder 中的顺序排列，
        // 未启用的非 fixed 任务追加在尾部（fixed last 任务之前）
        var allTasks = new List<string> { "StartGameTask", "TrailblazePowerTask", "ReceiveRewardsTask", "CosmicStrifeTask", "MissionAccomplishTask" };
        var newTabOrder = new List<string>();
        // 先按 TaskOrder 中的非 fixed 任务顺序排，fixed 任务钉在首尾
        var fixedFirst = allTasks.Where(t => t == "StartGameTask").ToList();
        var fixedLast = allTasks.Where(t => t == "MissionAccomplishTask").ToList();
        var orderedMiddle = order.Where(t => !FixedTasks.Contains(t) && allTasks.Contains(t)).ToList();
        var unorderedMiddle = allTasks.Where(t => !FixedTasks.Contains(t) && !orderedMiddle.Contains(t)).ToList();
        newTabOrder.AddRange(fixedFirst);
        newTabOrder.AddRange(orderedMiddle);
        newTabOrder.AddRange(unorderedMiddle);
        newTabOrder.AddRange(fixedLast);
        OrderedTabKeys = new AvaloniaList<string>(newTabOrder);

        // 刷新可移动状态
        for (var i = 0; i < order.Count; i++)
        {
            var name = order[i];
            var isFixed = FixedTasks.Contains(name);
            if (isFixed) continue;

            // 向左找：跳过 fixed，看是否存在非 fixed 的邻居
            var canLeft = false;
            for (var j = i - 1; j >= 0; j--)
            {
                if (!FixedTasks.Contains(order[j])) { canLeft = true; break; }
            }
            // 向右找：跳过 fixed，看是否存在非 fixed 的邻居
            var canRight = false;
            for (var j = i + 1; j < order.Count; j++)
            {
                if (!FixedTasks.Contains(order[j])) { canRight = true; break; }
            }

            switch (name)
            {
                case "TrailblazePowerTask":
                    IsTrailblazePowerCanMoveLeft = canLeft;
                    IsTrailblazePowerCanMoveRight = canRight;
                    break;
                case "ReceiveRewardsTask":
                    IsReceiveRewardsCanMoveLeft = canLeft;
                    IsReceiveRewardsCanMoveRight = canRight;
                    break;
                case "CosmicStrifeTask":
                    IsCosmicStrifeCanMoveLeft = canLeft;
                    IsCosmicStrifeCanMoveRight = canRight;
                    break;
            }
        }

        if (!order.Contains("TrailblazePowerTask")) { IsTrailblazePowerCanMoveLeft = false; IsTrailblazePowerCanMoveRight = false; }
        if (!order.Contains("ReceiveRewardsTask")) { IsReceiveRewardsCanMoveLeft = false; IsReceiveRewardsCanMoveRight = false; }
        if (!order.Contains("CosmicStrifeTask")) { IsCosmicStrifeCanMoveLeft = false; IsCosmicStrifeCanMoveRight = false; }
    }

    [RelayCommand]
    private void MoveTaskLeft(string taskClassName)
    {
        var order = CurrentConfig.TaskOrder;
        var idx = order.IndexOf(taskClassName);
        if (idx <= 0) return;

        // 找左边第一个非 fixed 的位置交换
        var targetIdx = idx - 1;
        while (targetIdx >= 0 && FixedTasks.Contains(order[targetIdx]))
            targetIdx--;
        if (targetIdx < 0) return;

        (order[idx], order[targetIdx]) = (order[targetIdx], order[idx]);
        OnPropertyChanged(nameof(CurrentConfig));
        RefreshTaskOrderItems();
    }

    [RelayCommand]
    private void MoveTaskRight(string taskClassName)
    {
        var order = CurrentConfig.TaskOrder;
        var idx = order.IndexOf(taskClassName);
        if (idx < 0 || idx >= order.Count - 1) return;

        // 找右边第一个非 fixed 的位置交换
        var targetIdx = idx + 1;
        while (targetIdx < order.Count && FixedTasks.Contains(order[targetIdx]))
            targetIdx++;
        if (targetIdx >= order.Count) return;

        (order[idx], order[targetIdx]) = (order[targetIdx], order[idx]);
        OnPropertyChanged(nameof(CurrentConfig));
        RefreshTaskOrderItems();
    }

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
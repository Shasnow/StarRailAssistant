using System.ComponentModel;
using System.Linq;
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

    [ObservableProperty] private Config _currentConfig;

    [ObservableProperty] private string _password = "";

    [ObservableProperty] [NotifyPropertyChangedFor(nameof(EnableContextMenu))]
    private object? _selectedTaskItem;

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
            if (args.PropertyName == nameof(Cache.CurrentConfigIndex))
            {
                _configService.SwitchConfig(_cacheService.Cache.ConfigNames[_cacheService.Cache.CurrentConfigIndex]);
                CurrentConfig = _configService.Config!;
            }
        }

        _cacheService.Cache.PropertyChanged += OnCachePropertyChanged;
        Tasks =
        [
            new TrailblazePowerTask(AddTaskItem)
            {
                Title = "培养目标",
                Cost = 40,
                CostText = "10-40",  // 培养目标可能是花萼(10)、虚影(30)、隧洞(40)
                Levels = new[] { "---选择副本---", "培养目标" },
                MaxSingleTimes = 6
            },

            new TrailblazePowerTask(AddTaskItem)
            {
                Title = "饰品提取",
                Cost = 40,
                Levels = new[]
                {
                    "---选择副本---",
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

            new TrailblazePowerTask(AddTaskItem)
            {
                Title = "拟造花萼（金）",
                Cost = 10,
                Levels = new[]
                {
                    "---选择副本---",
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

            new TrailblazePowerTask(AddTaskItem)
            {
                Title = "拟造花萼（赤）",
                Cost = 10,
                Levels = new[]
                {
                    "---选择副本---",
                    "月狂獠牙（毁灭）",
                    "净世残刃（毀灭）",
                    "神体琥珀（存护）",
                    "琥珀的坚守（存护）",
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
                    "阿赖耶华（记忆）"
                },
                MaxSingleTimes = 24
            },

            new TrailblazePowerTask(AddTaskItem)
            {
                Title = "凝滞虚影",
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

            new TrailblazePowerTask(AddTaskItem)
            {
                Title = "侵蚀隧洞",
                Cost = 40,
                Levels = new[]
                {
                    "---选择副本---",
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

            new TrailblazePowerTask(AddTaskItem)
            {
                Title = "历战余响",
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
    }

    public ControlPanelViewModel ControlPanelViewModel { get; }

    public AvaloniaList<TrailblazePowerTask> Tasks { get; }

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
            Level = task.SelectedIndex,
            LevelName = (task.Levels?.Cast<string>()!).ElementAtOrDefault(task.SelectedIndex) ?? string.Empty,
            Count = task.Count,
            RunTimes = task.RunTimes,
            AutoDetect = task.IsAutoDetect
        });
    }
}
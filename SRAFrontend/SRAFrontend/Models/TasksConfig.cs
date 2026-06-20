using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Text.Json.Serialization;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

public class TasksConfig
{
    [JsonPropertyName("name")] public string Name { get; set; } = "Default";
    [JsonPropertyName("startGame")] public StartGameConfig StartGame { get; init; } = new();
    [JsonPropertyName("trailblazePower")] public TrailblazePowerConfig TrailblazePower { get; init; } = new();
    [JsonPropertyName("receiveRewards")] public ReceiveRewardsConfig ReceiveRewards { get; init; } = new();
    [JsonPropertyName("cosmicStrife")] public CosmicStrifeConfig CosmicStrife { get; init; } = new();

    [JsonPropertyName("missionAccomplished")]
    public MissionAccomplishedConfig MissionAccomplished { get; init; } = new();

    [JsonPropertyName("version")] public int Version { get; init; } = StaticVersion;
    public static int StaticVersion => 4;
}

public partial class StartGameConfig : ObservableObject
{
    [ObservableProperty] [property: JsonPropertyName("enabled")]
    private bool _isEnabled = true;

    [ObservableProperty] [property: JsonPropertyName("game.channel")]
    private int _gameChannel;

    [ObservableProperty] [property: JsonPropertyName("game.path")]
    private string _gamePath = "";

    [ObservableProperty] [property: JsonPropertyName("game.useGlobalPath")]
    private bool _isUseGlobalGamePath = true;

    [ObservableProperty] [property: JsonPropertyName("autologin")]
    private bool _isAutoLogin = true;

    [ObservableProperty] [property: JsonPropertyName("relogin")]
    private bool _isReLogin = true;

    [JsonPropertyName("password")]
    public string EncryptedPassword { get; set; } = string.Empty;

    [JsonPropertyName("username")]
    public string EncryptedUsername { get; set; } = string.Empty;

    [ObservableProperty] [property: JsonIgnore]
    private string _password = "";

    [ObservableProperty] [property: JsonIgnore]
    private string _username = "";
}

public partial class TrailblazePowerConfig : ObservableObject
{
    [ObservableProperty] [property: JsonPropertyName("enabled")]
    private bool _isEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("replenish.enabled")]
    [property: Description("是否补充体力")]
    private bool _isReplenishEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("replenish.times")]
    [property: Description("补充体力的次数")]
    private int _replenishTimes;

    [ObservableProperty]
    [property: JsonPropertyName("replenish.way")]
    [property: Description("补充体力的方式，0-后备开拓力，1-燃料，2-星琼")]
    private int _replenishWay;

    [ObservableProperty]
    [property: JsonPropertyName("useAssistant")]
    [property: Description("是否使用支援角色")]
    private bool _isUseAssistant;

    [ObservableProperty]
    [property: JsonPropertyName("useBuildTarget")]
    [property: Description("是否启用培养目标，开启后将优先完成培养目标")]
    private bool _isUseBuildTarget;

    [JsonPropertyName("tasklist")]
    [Description("任务列表")]
    public ObservableCollection<TrailblazePowerTaskItem> TaskList { get; init; } = [];
    
    [ObservableProperty]
    [property: JsonPropertyName("activity.enabled")]
    [property: Description("是否启用多倍活动检测，启用后将优先刷取花藏繁生/异器盈界/位面分裂副本")]
    private bool _isActivityEnabled;
    
    [ObservableProperty]
    [property: JsonPropertyName("activity.gardenOfPlenty.level1")]
    [property: Description("花藏繁生中拟造花萼（金）的目标关卡")]
    private int _gardenOfPlentyLevel1;
    
    [ObservableProperty]
    [property: JsonPropertyName("activity.gardenOfPlenty.level2")]
    [property: Description("花藏繁生中拟造花萼（赤）的目标关卡")]
    private int _gardenOfPlentyLevel2;
    
    [ObservableProperty]
    [property: JsonPropertyName("activity.planarFissure.level")]
    [property: Description("位面分裂的目标关卡")]
    private int _planarFissureLevel;
    
    [ObservableProperty]
    [property: JsonPropertyName("activity.realmOfTheStrange.level")]
    [property: Description("异器盈界的目标关卡")]
    private int _realmOfTheStrangeLevel;
}

public partial class ReceiveRewardsConfig : ObservableObject
{
    [ObservableProperty] [property: JsonPropertyName("enabled")]
    private bool _isEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("redeemCodes")]
    [property: Description("兑换码列表，格式为：兑换码1 兑换码2 兑换码3")]
    private string _redeemCodes = "";

    [JsonPropertyName("rewards")]
    [Description("奖励列表，依次为：签证、派遣、邮件、每日实训、无名勋礼、巡星之礼、兑换码")]
    public ObservableCollection<bool> Rewards { get; init; } = [true, true, true, true, true, true, false];
}

public partial class CosmicStrifeConfig : ObservableObject
{
    [ObservableProperty] [property: JsonPropertyName("enabled")]
    private bool _isEnabled;
    
    [ObservableProperty]
    [property: JsonPropertyName("pointRewards.enabled")]
    [property: Description("是否启用积分奖励，启用后当达到周积分上限时跳过此任务")]
    private bool _isPointRewardsEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("divergentUniverse.enabled")]
    [property: Description("差分宇宙总开关")]
    private bool _isDivergentUniverseEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("divergentUniverse.mode")]
    [property: Description("差分宇宙模式，此字段没有实际作用")]
    private int _divergentUniverseMode;

    [ObservableProperty]
    [property: JsonPropertyName("divergentUniverse.runtimes")]
    [property: Description("差分宇宙运行次数")]
    private int _divergentUniverseRuntimes;

    [ObservableProperty]
    [property: JsonPropertyName("divergentUniverse.useTechnique")]
    [property: Description("差分宇宙是否使用秘技速刷")]
    private bool _isDivergentUniverseUseTechnique;

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.enabled")]
    [property: Description("货币战争总开关")]
    private bool _isCurrencyWarsEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.mode")]
    [property: Description("货币战争模式，0-标准博弈，1-超频博弈，2-刷开局")]
    private int _currencyWarsMode;

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.difficulty")]
    [property: Description("货币战争难度，0-最低难度，1-最高难度，2-当前难度")]
    private int _currencyWarsDifficulty;

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.reroll.bossAffixes")]
    [property: Description("货币战争刷开局时的Boss词缀")]
    private string _currencyWarsRerollBossAffixes = "";

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.reroll.bossNames")]
    [property: Description("货币战争刷开局时的Boss名称")]
    private string _currencyWarsRerollBossNames = "";

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.reroll.investEnvironments")]
    [property: Description("货币战争刷开局时的投资环境")]
    private string _currencyWarsRerollInvestEnvironments = "";

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.reroll.investStrategies")]
    [property: Description("货币战争刷开局时的投资策略")]
    private string _currencyWarsRerollInvestStrategies = "";

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.runtimes")]
    [property: Description("货币战争刷开局时的运行次数")]
    private int _currencyWarsRuntimes;

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.strategy")]
    [property: Description("货币战争使用的攻略名称")]
    private string _currencyWarsStrategy = "template";

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.strategyIndex")]
    [property: Description("货币战争使用的攻略索引")]
    private int _currencyWarsStrategyIndex;

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.username")]
    [property: Description("货币战争中开拓者的名字")]
    private string _currencyWarsUsername = "";
}

public partial class MissionAccomplishedConfig : ObservableObject
{
    [ObservableProperty] [property: JsonPropertyName("enabled")]
    private bool _isEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("exitApp")]
    [property: Description("完成任务后是否退出应用")]
    private bool _isExitApp;

    [ObservableProperty]
    [property: JsonPropertyName("exitGame")]
    [property: Description("完成任务后是否退出游戏")]
    private bool _isExitGame;

    [ObservableProperty]
    [property: JsonPropertyName("logout")]
    [property: Description("完成任务后是否登出账号")]
    private bool _isLogout;

    [ObservableProperty]
    [property: JsonPropertyName("shutdown")]
    [property: Description("完成任务后是否关机")]
    private bool _isShutdown;

    [ObservableProperty]
    [property: JsonPropertyName("sleep")]
    [property: Description("完成任务后是否睡眠")]
    private bool _isSleep;
}

public class TrailblazePowerTaskItem
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";
    [JsonPropertyName("level")]
    public int Level { get; set; }
    [JsonPropertyName("levelName")]
    public string LevelName { get; set; } = "";
    [JsonPropertyName("count")]
    public int Count { get; set; } = 1;
    [JsonPropertyName("runtimes")]
    public int RunTimes { get; set; }
    [JsonPropertyName("autoDetect")] 
    public bool AutoDetect { get; set; }
}
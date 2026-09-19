using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Text.Json.Serialization;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

public class TasksConfig
{
    [JsonPropertyName("name")]
    [Description("任务配置名称")]
    public string Name { get; set; } = "Default";

    [JsonPropertyName("startGame")]
    [Description("启动游戏配置")]
    public StartGameConfig StartGame { get; init; } = new();

    [JsonPropertyName("trailblazePower")]
    [Description("体力配置")]
    public TrailblazePowerConfig TrailblazePower { get; init; } = new();

    [JsonPropertyName("receiveRewards")]
    [Description("领取奖励配置")]
    public ReceiveRewardsConfig ReceiveRewards { get; init; } = new();

    [JsonPropertyName("cosmicStrife")]
    [Description("旷宇纷争配置")]
    public CosmicStrifeConfig CosmicStrife { get; init; } = new();

    [JsonPropertyName("missionAccomplished")]
    [Description("任务完成后操作")]
    public MissionAccomplishedConfig MissionAccomplished { get; init; } = new();

    [JsonPropertyName("version")]
    [Description("配置文件版本号")]
    public int Version { get; init; } = StaticVersion;

    public static int StaticVersion => 4;
}

public partial class StartGameConfig : ObservableObject
{
    [ObservableProperty]
    [property: JsonPropertyName("enabled")]
    [property: Description("是否启用启动游戏任务")]
    private bool _isEnabled = true;

    [ObservableProperty] [property: JsonPropertyName("game.channel")] [property: Description("游戏渠道，0-国服，1-B服，2-国际服")]
    private int _gameChannel;

    [ObservableProperty] [property: JsonPropertyName("game.path")] [property: Description("游戏启动程序路径")]
    private string _gamePath = "";

    [ObservableProperty]
    [property: JsonPropertyName("game.server")]
    [property: Description("国际服服务器，0-亚洲，1-欧洲，2-美洲，3-台港澳，仅国际服有效")]
    private int _gameServer;

    [ObservableProperty] [property: JsonPropertyName("game.useGlobalPath")] [property: Description("是否使用全局设置中的游戏路径")]
    private bool _isUseGlobalGamePath = true;

    [ObservableProperty] [property: JsonPropertyName("game.launchDelay")] [property: Description("启动游戏后的等待延迟（秒）")]
    private int _launchDelay = 5;

    [ObservableProperty] [property: JsonPropertyName("autologin")] [property: Description("是否自动登录账号")]
    private bool _isAutoLogin = true;

    [ObservableProperty] [property: JsonPropertyName("relogin")] [property: Description("是否在登录失败后自动重新登录")]
    private bool _isReLogin = true;

    [ObservableProperty] [property: JsonIgnore]
    private string _password = "";

    [ObservableProperty] [property: JsonIgnore]
    private string _username = "";

    [JsonPropertyName("password")]
    [Description("加密存储的账号密码")]
    public string EncryptedPassword { get; set; } = string.Empty;

    [JsonPropertyName("username")]
    [Description("加密存储的账号用户名")]
    public string EncryptedUsername { get; set; } = string.Empty;
}

public partial class TrailblazePowerConfig : ObservableObject
{
    [ObservableProperty] [property: JsonPropertyName("enabled")] [property: Description("是否启用开拓力任务")]
    private bool _isEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("activity.gardenOfPlenty.level1")]
    [property: Description("花藏繁生中拟造花萼（金）的目标关卡")]
    private int _gardenOfPlentyLevel1;

    [ObservableProperty]
    [property: JsonPropertyName("activity.gardenOfPlenty.level2")]
    [property: Description("花藏繁生中拟造花萼（赤）的目标关卡")]
    private int _gardenOfPlentyLevel2;

    [ObservableProperty] [property: JsonPropertyName("useAssistant")] [property: Description("是否使用支援角色")]
    private bool _isUseAssistant;

    [ObservableProperty] [property: JsonPropertyName("useBuildTarget")] [property: Description("是否启用培养目标，开启后将优先完成培养目标")]
    private bool _isUseBuildTarget;

    [ObservableProperty]
    [property: JsonPropertyName("activity.enabled")]
    [property: Description("是否启用多倍活动检测，启用后将优先刷取花藏繁生/异器盈界/位面分裂副本")]
    private bool _isActivityEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("activity.planarFissure.level")]
    [property: Description("位面分裂的目标关卡")]
    private int _planarFissureLevel;

    [ObservableProperty]
    [property: JsonPropertyName("activity.realmOfTheStrange.level")]
    [property: Description("异器盈界的目标关卡")]
    private int _realmOfTheStrangeLevel;

    [ObservableProperty] [property: JsonPropertyName("replenish.times")] [property: Description("补充体力的次数")]
    private int _replenishTimes;

    [ObservableProperty] [property: JsonPropertyName("replenish.enabled")] [property: Description("是否补充体力")]
    private bool _isReplenishEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("replenish.way")]
    [property: Description("补充体力的方式，0-后备开拓力，1-燃料，2-星琼")]
    private int _replenishWay;

    [JsonPropertyName("tasklist")]
    [Description("任务列表")]
    public ObservableCollection<TrailblazePowerTaskItem> TaskList { get; init; } = [];
}

public partial class ReceiveRewardsConfig : ObservableObject, IJsonOnDeserialized
{
    [ObservableProperty] [property: JsonPropertyName("enabled")] [property: Description("是否启用领取奖励任务")]
    private bool _isEnabled;

    [ObservableProperty] [property: JsonPropertyName("rewards.assignments")] [property: Description("是否领取派遣奖励")]
    private bool _isAssignmentsEnabled = true;

    [ObservableProperty] [property: JsonPropertyName("rewards.dailyTraining")] [property: Description("是否领取每日实训奖励")]
    private bool _isDailyTrainingEnabled = true;

    [ObservableProperty] [property: JsonPropertyName("rewards.giftOfOdyssey")] [property: Description("是否领取巡星之礼奖励")]
    private bool _isGiftOfOdysseyEnabled = true;

    [ObservableProperty] [property: JsonPropertyName("rewards.mail")] [property: Description("是否领取邮件奖励")]
    private bool _isMailEnabled = true;

    [ObservableProperty] [property: JsonPropertyName("rewards.namelessHonor")] [property: Description("是否领取无名勋礼奖励")]
    private bool _isNamelessHonorEnabled = true;

    [ObservableProperty] [property: JsonPropertyName("rewards.redeemCode")] [property: Description("是否执行兑换码兑换")]
    private bool _isRedeemCodeEnabled;

    [ObservableProperty] [property: JsonPropertyName("rewards.trailblazeProfile")] [property: Description("是否领取漫游签证奖励")]
    private bool _isTrailblazeProfileEnabled = true;

    [ObservableProperty] [property: JsonPropertyName("redeemCodes")] [property: Description("兑换码列表，格式为：兑换码1 兑换码2 兑换码3")]
    private string _redeemCodes = "";

    /// <summary>
    ///     旧版配置的奖励开关列表（索引依次为：签证、派遣、邮件、每日实训、无名勋礼、巡星之礼、兑换码）。
    ///     仅用于反序列化旧配置文件，序列化时不再写回。
    /// </summary>
    [JsonPropertyName("rewards")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ObservableCollection<bool>? Rewards { get; set; }

    /// <summary>旧版配置兼容：把旧 rewards 列表按索引映射到独立开关，越界索引保留默认值。</summary>
    public void OnDeserialized()
    {
        if (Rewards is not { Count: > 0 }) return;
        if (Rewards.Count > 0) IsTrailblazeProfileEnabled = Rewards[0];
        if (Rewards.Count > 1) IsAssignmentsEnabled = Rewards[1];
        if (Rewards.Count > 2) IsMailEnabled = Rewards[2];
        if (Rewards.Count > 3) IsDailyTrainingEnabled = Rewards[3];
        if (Rewards.Count > 4) IsNamelessHonorEnabled = Rewards[4];
        if (Rewards.Count > 5) IsGiftOfOdysseyEnabled = Rewards[5];
        if (Rewards.Count > 6) IsRedeemCodeEnabled = Rewards[6];
        Rewards = null;
    }
}

public partial class CosmicStrifeConfig : ObservableObject
{
    [ObservableProperty] [property: JsonPropertyName("enabled")] [property: Description("是否启用旷宇纷争任务")]
    private bool _isEnabled;

    [ObservableProperty] [property: JsonPropertyName("currencyWars.enabled")] [property: Description("货币战争总开关")]
    private bool _isCurrencyWarsEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.difficulty")]
    [property: Description("货币战争难度，0-最低难度，1-最高难度，2-当前难度")]
    private int _currencyWarsDifficulty;

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.mode")]
    [property: Description("货币战争模式，0-标准博弈，1-超频博弈，2-刷开局")]
    private int _currencyWarsMode;

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

    [ObservableProperty] [property: JsonPropertyName("currencyWars.runtimes")] [property: Description("货币战争刷开局时的运行次数")]
    private int _currencyWarsRuntimes;

    [ObservableProperty] [property: JsonPropertyName("currencyWars.strategy")] [property: Description("货币战争使用的攻略名称")]
    private string _currencyWarsStrategy = "template";

    [ObservableProperty]
    [property: JsonPropertyName("currencyWars.strategyIndex")]
    [property: Description("货币战争使用的攻略索引")]
    private int _currencyWarsStrategyIndex;

    [ObservableProperty] [property: JsonPropertyName("currencyWars.username")] [property: Description("货币战争中开拓者的名字")]
    private string _currencyWarsUsername = "";

    [ObservableProperty] [property: JsonPropertyName("divergentUniverse.enabled")] [property: Description("差分宇宙总开关")]
    private bool _isDivergentUniverseEnabled;

    [ObservableProperty]
    [property: JsonPropertyName("divergentUniverse.mode")]
    [property: Description("差分宇宙模式：0-刷单层，1-完整对局")]
    private int _divergentUniverseMode;

    [ObservableProperty] [property: JsonPropertyName("divergentUniverse.runtimes")] [property: Description("差分宇宙运行次数")]
    private int _divergentUniverseRuntimes;

    [ObservableProperty]
    [property: JsonPropertyName("divergentUniverse.useTechnique")]
    [property: Description("差分宇宙是否使用秘技速刷")]
    private bool _isDivergentUniverseUseTechnique;

    [ObservableProperty]
    [property: JsonPropertyName("pointRewards.enabled")]
    [property: Description("是否启用积分奖励，启用后当达到周积分上限时跳过此任务")]
    private bool _isPointRewardsEnabled;
}

public partial class MissionAccomplishedConfig : ObservableObject
{
    [ObservableProperty] [property: JsonPropertyName("enabled")] [property: Description("是否启用任务完成后操作")]
    private bool _isEnabled;

    [ObservableProperty] [property: JsonPropertyName("exitApp")] [property: Description("完成任务后是否退出应用")]
    private bool _isExitApp;

    [ObservableProperty] [property: JsonPropertyName("exitGame")] [property: Description("完成任务后是否退出游戏")]
    private bool _isExitGame;

    [ObservableProperty] [property: JsonPropertyName("logout")] [property: Description("完成任务后是否登出账号")]
    private bool _isLogout;

    [ObservableProperty] [property: JsonPropertyName("shutdown")] [property: Description("完成任务后是否关机")]
    private bool _isShutdown;

    [ObservableProperty] [property: JsonPropertyName("sleep")] [property: Description("完成任务后是否睡眠")]
    private bool _isSleep;
}

public class TrailblazePowerTaskItem
{
    [JsonPropertyName("name")]
    [Description("任务名称")]
    public string Name { get; set; } = "";

    [JsonPropertyName("id")]
    [Description("任务标识ID，如 calyx_golden、echo_of_war")]
    public string Id { get; set; } = "";

    [JsonPropertyName("level")]
    [Description("关卡等级")]
    public int Level { get; set; }

    [JsonPropertyName("levelName")]
    [Description("关卡名称")]
    public string LevelName { get; set; } = "";

    [JsonPropertyName("count")]
    [Description("手动模式下单个任务的执行次数")]
    public int Count { get; set; } = 1;

    [JsonPropertyName("runtimes")]
    [Description("手动模式下的执行轮数")]
    public int RunTimes { get; set; }

    [JsonPropertyName("autoDetect")]
    [Description("是否根据剩余体力自动分配执行次数")]
    public bool AutoDetect { get; set; }
}
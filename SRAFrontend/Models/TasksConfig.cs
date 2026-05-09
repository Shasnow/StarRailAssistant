using System.Collections.ObjectModel;
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

    [ObservableProperty] [property: JsonPropertyName("replenish.enabled")]
    private bool _isReplenishEnabled;

    [ObservableProperty] [property: JsonPropertyName("replenish.times")]
    private int _replenishTimes;

    [ObservableProperty] [property: JsonPropertyName("replenish.way")]
    private int _replenishWay;

    [ObservableProperty] [property: JsonPropertyName("useAssistant")]
    private bool _isUseAssistant;

    [ObservableProperty] [property: JsonPropertyName("useBuildTarget")]
    private bool _isUseBuildTarget;

    [JsonPropertyName("tasklist")]
    public ObservableCollection<TrailblazePowerTaskItem> TaskList { get; init; } = [];
}

public partial class ReceiveRewardsConfig : ObservableObject
{
    [ObservableProperty] [property: JsonPropertyName("enabled")]
    private bool _isEnabled;

    [ObservableProperty] [property: JsonPropertyName("redeemCodes")]
    private string _redeemCodes = "";

    [JsonPropertyName("rewards")]
    public ObservableCollection<bool> Rewards { get; init; } = [true, true, true, true, true, true, false];
}

public partial class CosmicStrifeConfig : ObservableObject
{
    [ObservableProperty] [property: JsonPropertyName("enabled")]
    private bool _isEnabled;
    
    [ObservableProperty] [property: JsonPropertyName("pointRewards.enabled")]
    private bool _isPointRewardsEnabled;

    [ObservableProperty] [property: JsonPropertyName("divergentUniverse.enabled")]
    private bool _isDivergentUniverseEnabled;

    [ObservableProperty] [property: JsonPropertyName("divergentUniverse.mode")]
    private int _divergentUniverseMode;

    [ObservableProperty] [property: JsonPropertyName("divergentUniverse.runtimes")]
    private int _divergentUniverseRuntimes;

    [ObservableProperty] [property: JsonPropertyName("divergentUniverse.useTechnique")]
    private bool _isDivergentUniverseUseTechnique;

    [ObservableProperty] [property: JsonPropertyName("currencyWars.enabled")]
    private bool _isCurrencyWarsEnabled;

    [ObservableProperty] [property: JsonPropertyName("currencyWars.mode")]
    private int _currencyWarsMode;

    [ObservableProperty] [property: JsonPropertyName("currencyWars.difficulty")]
    private int _currencyWarsDifficulty;

    [ObservableProperty] [property: JsonPropertyName("currencyWars.policy")]
    private int _currencyWarsPolicy;

    [ObservableProperty] [property: JsonPropertyName("currencyWars.reroll.bossAffixes")]
    private string _currencyWarsRerollBossAffixes = "";

    [ObservableProperty] [property: JsonPropertyName("currencyWars.reroll.bossNames")]
    private string _currencyWarsRerollBossNames = "";

    [ObservableProperty] [property: JsonPropertyName("currencyWars.reroll.investEnvironments")]
    private string _currencyWarsRerollInvestEnvironments = "";

    [ObservableProperty] [property: JsonPropertyName("currencyWars.reroll.investStrategies")]
    private string _currencyWarsRerollInvestStrategies = "";

    [ObservableProperty] [property: JsonPropertyName("currencyWars.runtimes")]
    private int _currencyWarsRuntimes;

    [ObservableProperty] [property: JsonPropertyName("currencyWars.strategy")]
    private string _currencyWarsStrategy = "template";

    [ObservableProperty] [property: JsonPropertyName("currencyWars.strategyIndex")]
    private int _currencyWarsStrategyIndex;

    [ObservableProperty] [property: JsonPropertyName("currencyWars.username")]
    private string _currencyWarsUsername = "";
}

public partial class MissionAccomplishedConfig : ObservableObject
{
    [ObservableProperty] [property: JsonPropertyName("enabled")]
    private bool _isEnabled;

    [ObservableProperty] [property: JsonPropertyName("exitApp")]
    private bool _isExitApp;

    [ObservableProperty] [property: JsonPropertyName("exitGame")]
    private bool _isExitGame;

    [ObservableProperty] [property: JsonPropertyName("logout")]
    private bool _isLogout;

    [ObservableProperty] [property: JsonPropertyName("shutdown")]
    private bool _isShutdown;

    [ObservableProperty] [property: JsonPropertyName("sleep")]
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
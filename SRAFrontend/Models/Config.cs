using System.Text.Json.Serialization;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

// 继承 ObservableObject 获得属性通知能力
public partial class Config : ObservableObject
{
    [ObservableProperty] private bool _afterExitApp; // 任务完成后退出 SRA
    [ObservableProperty] private bool _afterExitGame; // 任务完成后退出游戏

    [ObservableProperty] private bool _afterLogout; // 任务完成后是否登出
    [ObservableProperty] private bool _afterShutdown; // 任务完成后关机
    [ObservableProperty] private bool _afterSleep; // 任务完成后睡眠
    [ObservableProperty] private bool[] _enabledTasks = [true, false, false, false, false]; // 各任务启用状态

    [ObservableProperty] private string _name = "Default"; // 配置名称，默认为 "Default"
    [ObservableProperty] private string _receiveRewardRedeemCodes = ""; // 兑换码列表

    [ObservableProperty]
    private AvaloniaList<bool> _receiveRewards = [true, true, true, true, true, true, false]; // 各任务奖励领取状态

    // du - DifferentialUniverse 差分宇宙
    [ObservableProperty] private bool _dUEnable; // 是否启用模拟宇宙任务
    [ObservableProperty] private int _dUMode; // 模拟宇宙模式选择
    [ObservableProperty] private int _dUPolicy; // 模拟宇宙策略
    [ObservableProperty] private int _dURunTimes = 1; // 模拟宇宙运行次数
    [ObservableProperty] private bool _dUUseTechnique; // 差分宇宙是否使用秘技
    [ObservableProperty] private bool _currencyWarsEnable; // 是否启用货币战争任务
    [ObservableProperty] private int _currencyWarsMode; // 货币战争模式：0=标准博弈,1=超频博弈,2=刷开局（对应后端 CurrencyWarsMode）
    [ObservableProperty] private int _currencyWarsPolicy; // 货币战争策略
    [ObservableProperty] private int _currencyWarsRunTimes = 1; // 货币战争运行次数
    [ObservableProperty] private string _currencyWarsUsername = ""; // 货币战争用户名
    [ObservableProperty] private int _currencyWarsDifficulty; // 货币战争难度：0=最低难度，1=最高难度
    
    // 货币战争 - 刷开局 ps: CwRs = Currency wars Reroll start
    [ObservableProperty] private string _cwRsInvestEnvironments = ""; // 刷开局 - 期望投资环境，空格分隔
    [ObservableProperty] private string _cwRsInvestStrategies = ""; // 刷开局 - 期望投资策略，空格分隔
    [ObservableProperty] private int _cwRsInvestStrategyStage = 1; // 刷开局 - 期望投资策略阶段
    [ObservableProperty] private int _cwRsMaxRetry = 1; // 刷开局 - 最大尝试轮数

    [ObservableProperty] private bool _startGameAlwaysLogin; // 游戏启动时是否总是登录
    [ObservableProperty] private bool _startGameAutoLogin; // 启动游戏时是否自动登录
    [ObservableProperty] private int _startGameChannel; // 游戏启动通道
    [ObservableProperty] private string _startGamePath = ""; // 游戏启动路径
    [ObservableProperty] private bool _startGameUseGlobalPath = true; // 游戏启动是否使用全局路径

    [ObservableProperty] [property: JsonIgnore]
    private string _startGamePassword = ""; // 游戏启动密码

    [ObservableProperty] [property: JsonIgnore]
    private string _startGameUsername = ""; // 游戏启动用户名
    
    [ObservableProperty] private bool _trailblazePowerReplenishEnable; // 是否补充体力
    [ObservableProperty] private int _trailblazePowerReplenishTimes; // 补充体力次数
    [ObservableProperty] private int _trailblazePowerReplenishWay; // 补充体力方式

    [ObservableProperty] private AvaloniaList<TrailblazePowerTaskItem> _trailblazePowerTaskList = [];
    [ObservableProperty] private bool _trailblazePowerUseAssistant; // 是否使用助理
    [ObservableProperty] private bool _trailblazePowerUseBuildTarget; // 是否使用培养目标

    [JsonPropertyName("StartGamePassword")] public string EncryptedStartGamePassword { get; set; } = "";

    [JsonPropertyName("StartGameUsername")] public string EncryptedStartGameUsername { get; set; } = "";

    public int Version { get; init; } = StaticVersion; // 配置版本号
    public static int StaticVersion => 3;
}
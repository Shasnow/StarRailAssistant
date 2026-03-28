using System.Collections.Generic;
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

    /// <summary>
    ///     任务执行顺序：出现在列表中 = 启用，顺序 = 执行顺序。
    ///     使用类名（如 "StartGameTask"）标识任务，不依赖索引。
    ///     默认为空列表，由 DataPersister.LoadConfig 在迁移旧配置或新建配置时填充。
    /// </summary>
    [ObservableProperty] private List<string> _taskOrder = [];

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
    [ObservableProperty] private string _currencyWarsStrategy = "template"; // 货币战争攻略
    [ObservableProperty] private int _currencyWarsStrategyIndex;
    [ObservableProperty] private int _currencyWarsPolicy; // 货币战争策略
    [ObservableProperty] private int _currencyWarsRunTimes = 1; // 货币战争运行次数
    [ObservableProperty] private string _currencyWarsUsername = ""; // 货币战争用户名
    [ObservableProperty] private int _currencyWarsDifficulty; // 货币战争难度：0=最低难度，1=最高难度，2=当前难度（不切换难度）

    // 货币战争 - 刷开局 ps: CwRs = Currency wars Reroll start
    [ObservableProperty] private string _cwRsInvestEnvironments = ""; // 刷开局 - 期望投资环境，空格分隔
    [ObservableProperty] private string _cwRsInvestStrategies = ""; // 刷开局 - 期望投资策略，空格分隔
    [ObservableProperty] private string _cwRsBossNames = ""; // 刷开局 - 期望Boss名称，分号分隔，按第一位面;第二位面;第三位面填写
    [ObservableProperty] private string _cwRsBossAffixes = ""; // 刷开局 - 期望Boss词条，空格分隔
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
    public static int StaticVersion => 4;

    /// <summary>
    ///     检查指定任务是否在 TaskOrder 中（即是否启用）。
    ///     供 XAML CheckBox 绑定使用。
    /// </summary>
    public bool IsTaskEnabled(string taskName)
    {
        return TaskOrder.Contains(taskName);
    }

    /// <summary>
    ///     切换指定任务的启用状态：启用则加入 TaskOrder 末尾，禁用则移除。
    ///     供 XAML CheckBox 绑定使用。
    /// </summary>
    public void SetTaskEnabled(string taskName, bool enabled)
    {
        if (enabled && !TaskOrder.Contains(taskName))
        {
            TaskOrder.Add(taskName);
        }
        else if (!enabled)
        {
            TaskOrder.Remove(taskName);
        }
        OnPropertyChanged(nameof(TaskOrder));
    }
}

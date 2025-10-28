using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

// 继承 ObservableObject 获得属性通知能力
public partial class Config : ObservableObject
{
    [ObservableProperty] private bool[] _enabledTasks = [false, false, false, false, false]; // 各任务启用状态

    [ObservableProperty] private string _name = "Default"; // 配置名称，默认为 "Default"

    [ObservableProperty] private bool _startGameAlwaysLogin; // 游戏启动时是否总是登录
    [ObservableProperty] private bool _startGameAutoLogin; // 启动游戏时是否自动登录
    [ObservableProperty] private int _startGameChannel; // 游戏启动通道
    [ObservableProperty] private string _startGamePassword = ""; // 游戏启动密码
    [ObservableProperty] private string _startGamePath = ""; // 游戏启动路径
    [ObservableProperty] private string _startGameUsername = ""; // 游戏启动用户名

    [ObservableProperty] private AvaloniaList<TrailblazePowerTaskItem> _trailblazePowerTaskList = [];
    [ObservableProperty] private bool _trailblazePowerReplenishStamina; // 是否补充体力
    [ObservableProperty] private int _trailblazePowerReplenishWay; // 补充体力方式
    [ObservableProperty] private int _trailblazePowerReplenishTimes; // 补充体力次数
    [ObservableProperty] private bool _trailblazePowerUseAssistant; // 是否使用助理
    [ObservableProperty] private bool _trailblazePowerChangeLineup; // 是否更换阵容
    
    [ObservableProperty] private bool[] _receiveRewards = [false, false, false, false, false, false, false]; // 各任务奖励领取状态
    [ObservableProperty] private AvaloniaList<string> _receiveRewardRedeemCodes = []; // 兑换码列表
    
    [ObservableProperty] private int _simulatedUniverseMode; // 模拟宇宙模式选择
    [ObservableProperty] private int _simulatedUniverseTimes; // 模拟宇宙运行次数
    [ObservableProperty] private int _simulatedUniversePolicy; // 模拟宇宙策略
    
    [ObservableProperty] private bool _afterLogout; // 任务完成后是否登出
    [ObservableProperty] private bool _afterExitGame; // 任务完成后退出游戏
    [ObservableProperty] private bool _afterExitApp; // 任务完成后退出 SRA
    [ObservableProperty] private bool _afterSleep; // 任务完成后睡眠
    [ObservableProperty] private bool _afterShutdown; // 任务完成后关机

    public int Version { get; set; } = 3; // 配置版本号
}
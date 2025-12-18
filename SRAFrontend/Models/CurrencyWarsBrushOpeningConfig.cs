using System.Collections.Generic;

namespace SRAFrontend.Models;

/// <summary>
/// 货币战争 - 刷开局 配置模型。
/// 对应后端 Python 中 CurrencyWarsBrushOpening 配置块的结构。
/// </summary>
public class CurrencyWarsBrushOpeningConfig
{
    /// <summary>
    /// 期望的投资环境名称列表，例如 ["长线利好", "轮岗"]。
    /// </summary>
    public List<string> InvestEnvironment { get; set; } = new();

    /// <summary>
    /// 期望的投资策略名称列表，例如 ["砂里淘金"]。
    /// </summary>
    public List<string> InvestStrategy { get; set; } = new();

    /// <summary>
    /// 目标策略阶段（1 或 2），对应后端 InvestStrategyStage。
    /// </summary>
    public int InvestStrategyStage { get; set; } = 1;

    /// <summary>
    /// 最大尝试轮数，对应后端 RunTimes。
    /// 0 表示不限制，由后端自行控制。
    /// </summary>
    public int RunTimes { get; set; } = 0;
}



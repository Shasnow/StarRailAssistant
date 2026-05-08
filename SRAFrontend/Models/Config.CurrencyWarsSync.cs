namespace SRAFrontend.Models;

public partial class Config
{
    partial void OnCurrencyWarsObjectiveChanged(int value)
    {
        // 刷开局时固定走标准入口（与原逻辑一致），隐藏入口选项仅是 UI 表现。
        if (value == 1 && CurrencyWarsRuleset != 0)
            CurrencyWarsRuleset = 0;
        SyncCurrencyWarsPackedMode();
    }

    partial void OnCurrencyWarsRulesetChanged(int value) => SyncCurrencyWarsPackedMode();

    /// <summary>与 Python 后端约定：Mode = Objective×2 + Ruleset（0..3）。</summary>
    private void SyncCurrencyWarsPackedMode()
    {
        var packed = CurrencyWarsObjective * 2 + CurrencyWarsRuleset;
        if (CurrencyWarsMode != packed)
            CurrencyWarsMode = packed;
    }
}

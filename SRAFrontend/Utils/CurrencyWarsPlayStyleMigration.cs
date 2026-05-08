using SRAFrontend.Models;

namespace SRAFrontend.Utils;

/// <summary>
/// 将旧版单一 CurrencyWarsMode（0 标准刷等级 / 1 超频刷等级 / 2 刷开局标准）迁移为
/// CurrencyWarsObjective（0 刷等级 / 1 刷开局）+ CurrencyWarsRuleset（0 标准 / 1 超频），
/// 并同步打包字段 CurrencyWarsMode = Objective*2 + Ruleset（0..3）。
/// </summary>
public static class CurrencyWarsPlayStyleMigration
{
    public static void Apply(Config c)
    {
        if (c.CurrencyWarsObjective == 0 && c.CurrencyWarsRuleset == 0)
        {
            switch (c.CurrencyWarsMode)
            {
                case 1:
                    c.CurrencyWarsRuleset = 1;
                    break;
                case 2:
                    c.CurrencyWarsObjective = 1;
                    break;
                default:
                    if (c.CurrencyWarsMode >= 3)
                    {
                        c.CurrencyWarsObjective = 1;
                        c.CurrencyWarsRuleset = 1;
                    }
                    break;
            }
        }

        var packed = c.CurrencyWarsObjective * 2 + c.CurrencyWarsRuleset;
        if (c.CurrencyWarsMode != packed)
            c.CurrencyWarsMode = packed;
    }
}

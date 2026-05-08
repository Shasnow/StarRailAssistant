using SRAFrontend.Models;

namespace SRAFrontend.Utils;

/// <summary>
/// 将 main 旧配置迁移为新版三档：
/// 0 每次任务次数，1 每周总上限+每日尝试，2 刷满周期(OCR)+每日尝试。
///
/// main 旧策略索引按历史约定处理：
/// 0=每次，1=每日累计，2=每周累计，3=刷满周期。
/// </summary>
public static class CosmicStrifePolicyMigration
{
    public static void Apply(Config c)
    {
        c.DUPolicy = MapPolicy(c.DUPolicy);
        c.CurrencyWarsPolicy = MapPolicy(c.CurrencyWarsPolicy);
        if (c.DUWeeklyTotalCap <= 0)
            c.DUWeeklyTotalCap = 20;
        if (c.CurrencyWarsWeeklyTotalCap <= 0)
            c.CurrencyWarsWeeklyTotalCap = 3;
    }

    private static int MapPolicy(int p) => p switch
    {
        0 => 0,
        1 => 1,
        2 => 1,
        >= 3 => 2,
        _ => 0
    };
}

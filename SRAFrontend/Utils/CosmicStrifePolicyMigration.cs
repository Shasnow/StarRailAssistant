using SRAFrontend.Models;

namespace SRAFrontend.Utils;

/// <summary>
/// 将旧版旷宇纷争策略索引迁移为新版三档：0 每次任务次数，1 每周总上限+每日尝试，2 刷满周期(OCR)+每日尝试。
/// 旧版：0 每次，1 每日累计，2 每周累计，3 刷满周期。
/// 当前三档 UI 下 raw==2 已是「刷满周期」，MapPolicy 须输出 2（若仍映射为 1 则后端收不到 OCR 策略）。
/// </summary>
public static class CosmicStrifePolicyMigration
{
    public static void Apply(Config c)
    {
        c.DUPolicy = MapPolicy(c.DUPolicy);
        c.CurrencyWarsPolicy = MapPolicy(c.CurrencyWarsPolicy);
        if (c.DUWeeklyTotalCap <= 0)
            c.DUWeeklyTotalCap = 9999;
        if (c.CurrencyWarsWeeklyTotalCap <= 0)
            c.CurrencyWarsWeeklyTotalCap = 9999;
    }

    private static int MapPolicy(int p) => p switch
    {
        0 => 0,
        1 => 1,
        2 => 2,
        >= 3 => 2,
        _ => 0
    };
}

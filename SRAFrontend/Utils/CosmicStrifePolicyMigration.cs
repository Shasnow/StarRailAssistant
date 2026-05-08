using SRAFrontend.Models;

namespace SRAFrontend.Utils;

/// <summary>
/// 旷宇纷争策略字段与配置版本迁移。
/// 当前磁盘语义与 <see cref="Config.DUPolicy"/> / <see cref="Config.CurrencyWarsPolicy"/> 注释一致：三档 0/1/2。
/// 仅在 <see cref="Config.Version"/> &lt; 4 时，将历史上曾写入的「四档索引」转为上述三档（一次性）。
/// </summary>
public static class CosmicStrifePolicyMigration
{
    public const int ThreeTierPolicyConfigVersion = 4;

    public static void Apply(Config c)
    {
        if (c.Version < ThreeTierPolicyConfigVersion)
        {
            c.DUPolicy = MigrateLegacyFourSlotIndexToThreeTier(c.DUPolicy);
            c.CurrencyWarsPolicy = MigrateLegacyFourSlotIndexToThreeTier(c.CurrencyWarsPolicy);
            c.Version = ThreeTierPolicyConfigVersion;
        }

        if (c.DUWeeklyTotalCap <= 0)
            c.DUWeeklyTotalCap = 20;
        if (c.CurrencyWarsWeeklyTotalCap <= 0)
            c.CurrencyWarsWeeklyTotalCap = 3;
    }

    /// <summary>
    /// 旧四档编码（仅用于 v3 及更早磁盘文件）：0 每次 / 1 每日累计 / 2 每周累计 / 3 刷满周期 → 现三档 0/1/2。
    /// </summary>
    private static int MigrateLegacyFourSlotIndexToThreeTier(int p) => p switch
    {
        0 => 0,
        1 => 1,
        2 => 1,
        3 => 2,
        _ => int.Clamp(p, 0, 2)
    };
}

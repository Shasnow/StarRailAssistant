using System;
using System.Text.RegularExpressions;

namespace SRAFrontend.utilities;

/// <summary>
/// 语义化版本号（SemVer 2.0）解析工具
/// </summary>
public static class SemVerParser
{
    // SemVer 2.0 正则表达式
    private const string SemVerRegexPattern = @"^(v?)((0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*))(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$";
    private static readonly Regex SemVerRegex = new(SemVerRegexPattern, RegexOptions.Compiled | RegexOptions.IgnoreCase);

    /// <summary>
    /// 解析语义化版本号，返回结构化对象
    /// </summary>
    /// <param name="versionStr">原始版本字符串（如 v1.2.3-beta.1+build.456、1.0.0）</param>
    /// <returns>结构化 SemVer 信息，解析失败返回 null</returns>
    public static SemVerInfo? Parse(string? versionStr)
    {
        if (string.IsNullOrWhiteSpace(versionStr))
            return null;

        // 匹配正则
        var match = SemVerRegex.Match(versionStr.Trim());
        if (!match.Success)
            return null;

        // 提取各分组（注意分组索引对应关系）
        return new SemVerInfo
        {
            Original = versionStr.Trim(), // 原始版本字符串
            Major = int.TryParse(match.Groups[3].Value, out var major) ? major : 0,
            Minor = int.TryParse(match.Groups[4].Value, out var minor) ? minor : 0,
            Patch = int.TryParse(match.Groups[5].Value, out var patch) ? patch : 0,
            PreRelease = string.IsNullOrWhiteSpace(match.Groups[6].Value) ? null : match.Groups[6].Value,
            BuildMetadata = string.IsNullOrWhiteSpace(match.Groups[7].Value) ? null : match.Groups[7].Value,
            HasVPrefix = !string.IsNullOrWhiteSpace(match.Groups[1].Value) // 是否包含 v 前缀
        };
    }

    /// <summary>
    /// 验证版本字符串是否符合 SemVer 2.0 规范
    /// </summary>
    public static bool IsValidSemVer(string? versionStr)
    {
        if (string.IsNullOrWhiteSpace(versionStr))
            return false;
        return SemVerRegex.IsMatch(versionStr.Trim());
    }
}

/// <summary>
/// 结构化的语义化版本号信息
/// </summary>
public class SemVerInfo
{
    /// <summary>原始版本字符串（如 v1.2.3-beta.1+build.456）</summary>
    public string Original { get; set; } = string.Empty;

    /// <summary>主版本号（Major）</summary>
    public int Major { get; init; }

    /// <summary>次版本号（Minor）</summary>
    public int Minor { get; init; }

    /// <summary>修订号（Patch）</summary>
    public int Patch { get; init; }

    /// <summary>预发布版本（PreRelease，如 beta.1）</summary>
    public string? PreRelease { get; init; }

    /// <summary>构建元数据（BuildMetadata，如 build.456）</summary>
    public string? BuildMetadata { get; init; }

    /// <summary>是否包含 v 前缀</summary>
    public bool HasVPrefix { get; set; }

    /// <summary>转换为标准 Version 对象（忽略预发布和构建元数据）</summary>
    public Version ToVersion() => new Version(Major, Minor, Patch);

    /// <summary>转换为标准 SemVer 字符串（无 v 前缀，包含预发布和构建元数据）</summary>
    public override string ToString()
    {
        var baseVersion = $"{Major}.{Minor}.{Patch}";
        if (PreRelease != null)
            baseVersion += $"-{PreRelease}";
        if (BuildMetadata != null)
            baseVersion += $"+{BuildMetadata}";
        return baseVersion;
    }

    /// <summary>版本比较（遵循 SemVer 2.0 规范）</summary>
    public int CompareTo(SemVerInfo? other)
    {
        if (other == null)
            return 1;

        // 先比较主、次、修订号
        var versionCompare = ToVersion().CompareTo(other.ToVersion());
        if (versionCompare != 0)
            return versionCompare;

        // 无预发布版本 > 有预发布版本（如 1.2.3 > 1.2.3-beta）
        if (PreRelease == null && other.PreRelease != null)
            return 1;
        if (PreRelease != null && other.PreRelease == null)
            return -1;

        // 比较预发布版本（按点分割，数字优先）
        if (PreRelease != null && other.PreRelease != null)
            return ComparePreRelease(PreRelease, other.PreRelease);

        // 构建元数据不参与版本比较
        return 0;
    }

    /// <summary>预发布版本比较（遵循 SemVer 规范）</summary>
    private int ComparePreRelease(string pre1, string pre2)
    {
        var parts1 = pre1.Split('.');
        var parts2 = pre2.Split('.');
        var maxLength = Math.Max(parts1.Length, parts2.Length);

        for (var i = 0; i < maxLength; i++)
        {
            var part1 = i < parts1.Length ? parts1[i] : string.Empty;
            var part2 = i < parts2.Length ? parts2[i] : string.Empty;

            // 数字部分按数值比较，非数字按字符串比较
            if (int.TryParse(part1, out var num1) && int.TryParse(part2, out var num2))
            {
                if (num1 != num2)
                    return num1.CompareTo(num2);
            }
            else
            {
                var strCompare = string.Compare(part1, part2, StringComparison.Ordinal);
                if (strCompare != 0)
                    return strCompare;
            }
        }

        return 0;
    }
    
    public static bool operator >(SemVerInfo left, SemVerInfo right) => left.CompareTo(right) > 0;
    public static bool operator <(SemVerInfo left, SemVerInfo right) => left.CompareTo(right) < 0;
    public static bool operator >=(SemVerInfo left, SemVerInfo right) => left.CompareTo(right) >= 0;
    public static bool operator <=(SemVerInfo left, SemVerInfo right) => left.CompareTo(right) <= 0;
}
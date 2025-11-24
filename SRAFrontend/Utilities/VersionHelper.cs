using System;

namespace SRAFrontend.utilities;

public static class VersionHelper
{
    /// <summary>
    /// 判断是否为热修复版本（主版本、次版本与当前版本一致）
    /// </summary>
    public static bool IsHotfix(SemVerInfo currentVersion, SemVerInfo newVersion)
    {
        // 主版本和次版本必须相同
        if (newVersion.Major != currentVersion.Major || newVersion.Minor != currentVersion.Minor)
            return false;
    
        // 修订号必须不同
        if (newVersion.Patch == currentVersion.Patch)
            return false;
    
        // 不能有预发布版本的变化（要么都没有，要么都有且相同）
        if (currentVersion.PreRelease != newVersion.PreRelease)
        {
            // 如果其中一个有预发布版本而另一个没有，则不是热修复
            if (string.IsNullOrEmpty(currentVersion.PreRelease) || string.IsNullOrEmpty(newVersion.PreRelease))
                return false;
        }
    
        return true;
    }

    /// <summary>
    /// 判断是否需要更新（新版本 > 当前版本，且未安装该热修复）
    /// </summary>
    public static bool NeedUpdate(SemVerInfo currentVersion, SemVerInfo newVersion, string installedHotfixVersion)
    {
        return currentVersion < newVersion;
        // 这些是以后可能用到的妙妙小代码
        // // 1. 新版本 <= 当前版本 → 无需更新
        // if (newVersion <= currentVersion)
        // {
        //     return false;
        // }
        //
        // // 2. 已安装该热修复 → 无需更新
        // var installedHotfix = SemVerParser.Parse(installedHotfixVersion);
        // return installedHotfix == null || installedHotfix != newVersion;
    }

    /// <summary>
    /// 获取版本显示文本（区分主版本和热修复版本）
    /// </summary>
    public static string GetVersionDisplayText(SemVerInfo currentVersion, SemVerInfo? installedHotfixVersion)
    {
        if (installedHotfixVersion == null) return $"当前版本：{currentVersion}";
        return currentVersion > installedHotfixVersion
            ? $"当前版本：{currentVersion}"
            : $"热修复：{installedHotfixVersion}";
    }
}
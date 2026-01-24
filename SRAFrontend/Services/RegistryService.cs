using System;
using System.Runtime.InteropServices;
using System.Security;
using System.Security.AccessControl;
using System.Text;
using Microsoft.Extensions.Logging;
using Microsoft.Win32;

namespace SRAFrontend.Services;

/// <summary>
///     Windows 注册表服务, 用于读取和写入注册表项
/// </summary>
public class RegistryService(
    ILogger<RegistryService> logger,
    CacheService cacheService,
    SettingsService settingsService)
{
    // 注册表键名常量
     private static class RegistryKeys
     {
         // 分辨率相关子键
         public const string GameResolutionSubKey = @"Software\miHoYo\崩坏：星穹铁道";
         // 分辨率相关值名称
         public const string GraphicsSettingsPcResolution = "GraphicsSettings_PCResolution_h431323223";
         public const string ScreenManagerResolutionWidth = "Screenmanager Resolution Width_h182942802";
         public const string ScreenManagerResolutionHeight = "Screenmanager Resolution Height_h2627697771";
         public const string ScreenManagerFullscreenMode = "Screenmanager Fullscreen mode_h3630240806";
         // 游戏安装路径相关子键（优先级从高到低）
         public static readonly string[] GameInstallPathSubKeys =
         [
             @"Software\miHoYo\HYP\standalone\14_0\hkrpg_cn\6P5gHMNyK3\hkrpg_cn",
             @"Software\miHoYo\HYP\1_1\hkrpg_cn"
         ];
     }
    // 提示文本常量
    private const string CanNotDetectGamePath = "无法自动检测游戏路径";
    private const string RegistryKeyAccessDenied = "注册表访问被拒绝（请以管理员身份运行）";

    /// <summary>
    ///     获取星穹铁道游戏安装路径（自动适配多注册表路径）
    /// </summary>
    /// <returns>游戏可执行文件路径，失败返回提示文本</returns>
    public string GetGameInstallPath()
    {
        // 非Windows系统直接返回
        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            logger.LogWarning("Registry operations are not supported on non-Windows systems");
            return CanNotDetectGamePath;
        }

        logger.LogInformation("Start detecting game installation path");

        try
        {
            using var currentUserKey = Registry.CurrentUser;

            // 遍历所有可能的注册表路径，优先匹配第一个存在的
            foreach (var subKeyPath in RegistryKeys.GameInstallPathSubKeys)
            {
                using var gameSubKey = currentUserKey.OpenSubKey(subKeyPath);
                if (gameSubKey == null)
                {
                    logger.LogDebug("Registry key not found: {SubKeyPath}", subKeyPath);
                    continue;
                }

                // 读取游戏安装路径
                var gameInstallPath = gameSubKey.GetValue("GameInstallPath") as string;
                if (!string.IsNullOrEmpty(gameInstallPath))
                {
                    // 格式化路径（替换反斜杠为正斜杠，拼接可执行文件）
                    var fullExePath = $"{gameInstallPath.Replace('\\', '/')}/StarRail.exe";
                    logger.LogInformation("Game path detected successfully: {Path}", fullExePath);
                    return fullExePath;
                }

                logger.LogDebug("GameInstallPath value not found in registry key: {SubKeyPath}", subKeyPath);
            }

            logger.LogWarning("No valid game installation path found in all registry locations");
            return CanNotDetectGamePath;
        }
        catch (SecurityException ex)
        {
            logger.LogError(ex, "Registry access denied (please run as administrator)");
            return RegistryKeyAccessDenied;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "An error occurred while detecting game installation path");
            return $"{CanNotDetectGamePath}: {ex.Message}";
        }
    }

    /// <summary>
    ///     设置目标分辨率到注册表（先备份原有配置到缓存）
    /// </summary>
    /// <returns>是否设置成功</returns>
    public bool SetTargetPcResolution()
    {
        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            logger.LogWarning("Registry operations are not supported on non-Windows systems");
            return false;
        }
        try
        {
            using var currentUserKey = Registry.CurrentUser;
            using var gameResolutionKey = currentUserKey.OpenSubKey(
                RegistryKeys.GameResolutionSubKey,
                RegistryKeyPermissionCheck.ReadWriteSubTree,
                RegistryRights.WriteKey | RegistryRights.ReadKey);

            if (gameResolutionKey == null)
            {
                logger.LogError("Registry key not found: {key}", RegistryKeys.GameResolutionSubKey);
                return false;
            }
            // 备份原有分辨率配置到缓存
            BackupCurrentResolution(gameResolutionKey);

            // 从配置读取目标分辨率
            var screenSize = settingsService.Settings.LaunchArgumentsScreenSize.Split('x');
            var width = int.Parse(screenSize[0]);
            var height = int.Parse(screenSize[1]);

            // 显示模式转换
            // "窗口化" -> 3, "全屏窗口" -> 1, "独占全屏" -> 0
            var fullscreenMode = settingsService.Settings.LaunchArgumentsFullScreenMode switch
            {
                "独占全屏" => 0,
                "全屏窗口" => 1,
                _ => 3
            };
            var isFullScreen = fullscreenMode != 3;

            // 写入目标分辨率配置
            logger.LogInformation(
                "Start setting target resolution: Width={Width}, Height={Height}, FullscreenMode={Mode}, IsFullScreen={IsFullScreen}",
                width, height, fullscreenMode, isFullScreen);

            var targetPcResolutionJson = $"{{\"width\":{width},\"height\":{height},\"isFullScreen\":{isFullScreen.ToString().ToLower()}}}\0";
            var binaryTargetPcResolution = Encoding.ASCII.GetBytes(targetPcResolutionJson);

            gameResolutionKey.SetValue(RegistryKeys.GraphicsSettingsPcResolution, binaryTargetPcResolution,
                RegistryValueKind.Binary);
            gameResolutionKey.SetValue(RegistryKeys.ScreenManagerResolutionWidth, width,
                RegistryValueKind.DWord);
            gameResolutionKey.SetValue(RegistryKeys.ScreenManagerResolutionHeight, height,
                RegistryValueKind.DWord);
            gameResolutionKey.SetValue(RegistryKeys.ScreenManagerFullscreenMode, fullscreenMode,
                RegistryValueKind.DWord);

            logger.LogInformation("Target resolution set successfully");
            cacheService.Cache.IsGameResolutionChanged = true; // 标记分辨率已更改
            return true;
        }
        catch (SecurityException ex)
        {
            logger.LogError(ex, "Registry access denied (please run as administrator)");
            return false;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "An error occurred while restoring original resolution");
            return false;
        }
    }

    /// <summary>
    ///     从缓存恢复用户原有分辨率配置到注册表
    /// </summary>
    /// <returns>是否恢复成功</returns>
    public bool RestoreUserPcResolution()
    {
        if (!cacheService.Cache.IsGameResolutionChanged) return true; // 未更改分辨率无需恢复
        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            logger.LogWarning("Registry operations are not supported on non-Windows systems");
            return false;
        }
        // 校验缓存中的备份数据是否完整
        if (cacheService.Cache.UserGameResolution == null ||
            cacheService.Cache.UserGameResolutionWidth == null ||
            cacheService.Cache.UserGameResolutionHeight == null ||
            cacheService.Cache.UserGameFullscreenMode == null)
        {
            logger.LogWarning("No valid resolution backup found in cache, restore failed");
            return false;
        }
        try
        {
            using var currentUserKey = Registry.CurrentUser;
            using var gameResolutionKey = currentUserKey.OpenSubKey(
                RegistryKeys.GameResolutionSubKey,
                RegistryKeyPermissionCheck.ReadWriteSubTree,
                RegistryRights.WriteKey | RegistryRights.ReadKey);

            if (gameResolutionKey == null)
            {
                logger.LogError("Registry key not found: {key}", RegistryKeys.GameResolutionSubKey);
                return false;
            }
            // 写入缓存中的原有配置
            logger.LogInformation(
                "Start restoring original resolution: Width={Width}, Height={Height}, FullscreenMode={Mode}",
                cacheService.Cache.UserGameResolutionWidth,
                cacheService.Cache.UserGameResolutionHeight,
                cacheService.Cache.UserGameFullscreenMode);

            gameResolutionKey.SetValue(RegistryKeys.GraphicsSettingsPcResolution, cacheService.Cache.UserGameResolution,
                RegistryValueKind.Binary);
            gameResolutionKey.SetValue(RegistryKeys.ScreenManagerResolutionWidth,
                cacheService.Cache.UserGameResolutionWidth, RegistryValueKind.DWord);
            gameResolutionKey.SetValue(RegistryKeys.ScreenManagerResolutionHeight,
                cacheService.Cache.UserGameResolutionHeight, RegistryValueKind.DWord);
            gameResolutionKey.SetValue(RegistryKeys.ScreenManagerFullscreenMode,
                cacheService.Cache.UserGameFullscreenMode, RegistryValueKind.DWord);

            logger.LogInformation("Original resolution restored successfully");
            return true;
        }
        catch (SecurityException ex)
        {
            logger.LogError(ex, "Registry access denied (please run as administrator)");
            return false;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "An error occurred while restoring original resolution");
            return false;
        }
    }

    /// <summary>
    ///     备份当前注册表中的分辨率配置到缓存
    /// </summary>
    /// <param name="gameResolutionKey">已打开的分辨率注册表项</param>
    private void BackupCurrentResolution(RegistryKey gameResolutionKey)
    {
        try
        {
            if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows)) return;
            // 读取当前注册表值
            var currentPcResolution = gameResolutionKey.GetValue(RegistryKeys.GraphicsSettingsPcResolution) as byte[];
            var currentWidth = gameResolutionKey.GetValue(RegistryKeys.ScreenManagerResolutionWidth) as int?;
            var currentHeight = gameResolutionKey.GetValue(RegistryKeys.ScreenManagerResolutionHeight) as int?;
            var currentFullscreenMode = gameResolutionKey.GetValue(RegistryKeys.ScreenManagerFullscreenMode) as int?;

            // 写入缓存
            cacheService.Cache.UserGameResolution = currentPcResolution;
            cacheService.Cache.UserGameResolutionWidth = currentWidth;
            cacheService.Cache.UserGameResolutionHeight = currentHeight;
            cacheService.Cache.UserGameFullscreenMode = currentFullscreenMode;

            logger.LogInformation(
                "Current resolution backed up to cache successfully: Width={Width}, Height={Height}, FullscreenMode={Mode}",
                currentWidth, currentHeight, currentFullscreenMode);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "An error occurred while backing up current resolution to cache");
        }
    }


}
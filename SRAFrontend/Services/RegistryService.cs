using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Security;
using System.Security.AccessControl;
using System.Text;
using Microsoft.Extensions.Logging;
using Microsoft.Win32;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

/// <summary>
///     Windows 注册表服务（星穹铁道分辨率/游戏路径管理）
/// </summary>
public class RegistryService(
    ILogger<RegistryService> logger,
    CacheService cacheService,
    SettingsService settingsService)
{
    // 提示文本
    private const string MsgUnsupportedOs = "非Windows系统不支持注册表操作";
    private const string MsgGamePathNotFound = "无法自动检测游戏路径";
    private const string MsgAccessDenied = "注册表访问被拒绝，请以管理员身份运行";
    private const string MsgRegKeyNotFound = "未找到注册表项: {key}";

    /// <summary>
    ///     获取星穹铁道游戏安装路径
    /// </summary>
    public List<string> GetGameInstallPaths()
    {
        var result = new List<string>();

        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            logger.LogWarning(MsgUnsupportedOs);
            result.Add(MsgGamePathNotFound);
            return result;
        }

        foreach (var path in RegistryConfig.GameInstallPathKeys)
            try
            {
                using var subKey = Registry.CurrentUser.OpenSubKey(path);
                if (subKey == null)
                {
                    logger.LogDebug("The registry key does not exist: {Path}", path);
                    continue;
                }

                var installPath = subKey.GetValue("GameInstallPath") as string;
                if (string.IsNullOrWhiteSpace(installPath))
                {
                    logger.LogDebug("GameInstallPath is null: {Path}", path);
                    continue;
                }

                var exeFullPath = Path.Combine(installPath, "StarRail.exe").Replace('\\', '/');

                // 去重
                if (!result.Exists(p => p.Equals(exeFullPath, StringComparison.OrdinalIgnoreCase)))
                {
                    result.Add(exeFullPath);
                    logger.LogInformation("Game path detected: {Path}", exeFullPath);
                }
            }
            catch (SecurityException ex)
            {
                logger.LogError(ex, MsgAccessDenied);
                result.Add(MsgAccessDenied);
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Failed to read the registry: {Path}", path);
            }

        return result;
    }

    /// <summary>
    ///     统一设置国服+国际服分辨率
    /// </summary>
    public void SetTargetPcResolution()
    {
        SetResolutionForServer(RegistryConfig.CnGameRegPath);
        SetResolutionForServer(RegistryConfig.GlobalGameRegPath);
    }

    /// <summary>
    ///     统一恢复国服+国际服分辨率
    /// </summary>
    public void RestoreUserPcResolution()
    {
        RestoreResolutionForServer(RegistryConfig.CnGameRegPath);
        RestoreResolutionForServer(RegistryConfig.GlobalGameRegPath);
    }

    /// <summary>
    ///     设置单个服的分辨率
    /// </summary>
    private void SetResolutionForServer(string regPath)
    {
        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            logger.LogWarning(MsgUnsupportedOs);
            return;
        }

        try
        {
            using var key = OpenWritableKey(regPath);
            if (key == null)
            {
                logger.LogError(MsgRegKeyNotFound, regPath);
                return;
            }

            // 备份原有配置
            BackupResolution(regPath, key);

            // 读取目标配置
            var size = settingsService.Settings.General.GameArgsWindowSize.Split('x');
            var w = int.TryParse(size[0], out var width) ? width : 1920;
            var h = int.TryParse(size[1], out var height) ? height : 1080;

            var fullscreenMode = settingsService.Settings.General.GameArgsFullScreenMode == "全屏" ? 1 : 3;
            var isFull = fullscreenMode != 3;

            logger.LogInformation("Write resolution {W}x{H} Fullscreen:{Full}", w, h, isFull);

            // 写入二进制JSON
            var json = $"{{\"width\":{w},\"height\":{h},\"isFullScreen\":{isFull.ToString().ToLower()}}}\0";
            var bytes = Encoding.ASCII.GetBytes(json);

            key.SetValue(RegistryConfig.GraphicsSettingsPcResolution, bytes, RegistryValueKind.Binary);
            key.SetValue(RegistryConfig.ScreenManagerResolutionWidth, w, RegistryValueKind.DWord);
            key.SetValue(RegistryConfig.ScreenManagerResolutionHeight, h, RegistryValueKind.DWord);
            key.SetValue(RegistryConfig.ScreenManagerFullscreenMode, fullscreenMode, RegistryValueKind.DWord);

            cacheService.Cache.IsGameResolutionChanged = true;
        }
        catch (SecurityException ex)
        {
            logger.LogError(ex, MsgAccessDenied);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to set resolution");
        }
    }

    /// <summary>
    ///     恢复单个服分辨率
    /// </summary>
    private void RestoreResolutionForServer(string regPath)
    {
        if (!cacheService.Cache.IsGameResolutionChanged) return;

        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            logger.LogWarning(MsgUnsupportedOs);
            return;
        }

        var cache = GetResolutionCache(regPath);

        // 校验缓存是否有效
        if (cache.Resolution == null || cache.Width == null || cache.Height == null || cache.FullscreenMode == null)
        {
            logger.LogWarning("No valid resolution backup, skipping recovery");
            return;
        }

        try
        {
            using var key = OpenWritableKey(regPath);
            if (key == null)
            {
                logger.LogError(MsgRegKeyNotFound, regPath);
                return;
            }

            logger.LogInformation("Restore resolution: {W}x{H}", cache.Width, cache.Height);

            key.SetValue(RegistryConfig.GraphicsSettingsPcResolution, cache.Resolution, RegistryValueKind.Binary);
            key.SetValue(RegistryConfig.ScreenManagerResolutionWidth, cache.Width.Value, RegistryValueKind.DWord);
            key.SetValue(RegistryConfig.ScreenManagerResolutionHeight, cache.Height.Value, RegistryValueKind.DWord);
            key.SetValue(RegistryConfig.ScreenManagerFullscreenMode, cache.FullscreenMode.Value,
                RegistryValueKind.DWord);
        }
        catch (SecurityException ex)
        {
            logger.LogError(ex, MsgAccessDenied);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to restore resolution");
        }
    }

    /// <summary>
    ///     备份当前分辨率到缓存
    /// </summary>
    private void BackupResolution(string regPath, RegistryKey key)
    {
        try
        {
            var cache = GetResolutionCache(regPath);
            if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows)) return;
            cache.Resolution = key.GetValue(RegistryConfig.GraphicsSettingsPcResolution) as byte[];
            cache.Width = key.GetValue(RegistryConfig.ScreenManagerResolutionWidth) as int?;
            cache.Height = key.GetValue(RegistryConfig.ScreenManagerResolutionHeight) as int?;
            cache.FullscreenMode = key.GetValue(RegistryConfig.ScreenManagerFullscreenMode) as int?;

            SaveResolutionCache(regPath, cache);

            logger.LogInformation("Backup resolution: {W}x{H}", cache.Width, cache.Height);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Backup resolution failed");
        }
    }

    /// <summary>
    ///     打开可写注册表项
    /// </summary>
    private RegistryKey? OpenWritableKey(string path)
    {
        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows)) return null;
        return Registry.CurrentUser.OpenSubKey(
            path,
            RegistryKeyPermissionCheck.ReadWriteSubTree,
            RegistryRights.WriteKey | RegistryRights.ReadKey);
    }

    /// <summary>
    ///     获取对应服的缓存
    /// </summary>
    private ResolutionCache GetResolutionCache(string regPath)
    {
        return regPath == RegistryConfig.CnGameRegPath
            ? cacheService.Cache.CnGameResolution
            : cacheService.Cache.GlobalGameResolution;
    }

    /// <summary>
    ///     保存缓存
    /// </summary>
    private void SaveResolutionCache(string regPath, ResolutionCache cache)
    {
        if (regPath == RegistryConfig.CnGameRegPath)
            cacheService.Cache.CnGameResolution = cache;
        else
            cacheService.Cache.GlobalGameResolution = cache;
    }

    /// <summary>
    ///     注册表常量配置
    /// </summary>
    private static class RegistryConfig
    {
        // 游戏服注册表路径
        public const string CnGameRegPath = @"Software\miHoYo\崩坏：星穹铁道";
        public const string GlobalGameRegPath = @"Software\Cognosphere\Star Rail";

        // 分辨率键名
        public const string GraphicsSettingsPcResolution = "GraphicsSettings_PCResolution_h431323223";
        public const string ScreenManagerResolutionWidth = "Screenmanager Resolution Width_h182942802";
        public const string ScreenManagerResolutionHeight = "Screenmanager Resolution Height_h2627697771";
        public const string ScreenManagerFullscreenMode = "Screenmanager Fullscreen mode_h3630240806";

        // 游戏安装路径搜索列表
        public static readonly string[] GameInstallPathKeys =
        [
            @"Software\miHoYo\HYP\standalone\14_0\hkrpg_cn\6P5gHMNyK3\hkrpg_cn",
            @"Software\miHoYo\HYP\1_1\hkrpg_cn",
            @"Software\Cognosphere\HYP\1_1\hkrpg_global",
            @"Software\Cognosphere\HYP\1_0\hkrpg_global"
        ];
    }
}


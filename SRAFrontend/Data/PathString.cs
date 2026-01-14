using System;
using System.IO;
using System.Runtime.InteropServices;

namespace SRAFrontend.Data;

/// <summary>
/// 路径字符串常量
/// </summary>
public static class PathString
{
    public static readonly string AppDataSraDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "SRA");
    public static readonly string TempSraDir = Path.Combine(Path.GetTempPath(), "SRA");
    public static readonly string SettingsJson = Path.Combine(AppDataSraDir, "settings.json");
    public static readonly string CacheJson = Path.Combine(AppDataSraDir, "cache.json");
    public static readonly string ConfigsDir = Path.Combine(AppDataSraDir, "configs");
    public static readonly string FrontendLogsDir = Path.Combine(AppDataSraDir, "logs");
    public static readonly string BackendLogsDir = Path.Combine(Environment.CurrentDirectory, "log");
    public static readonly string ReportsDir = "reports";
    public static readonly string SourceCodeDir = Path.Combine(Environment.CurrentDirectory, "SRA");

    public static string SraExecutablePath
    {
        get
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                return Path.Combine(Environment.CurrentDirectory, "SRA.exe");
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
                return Path.Combine(Environment.CurrentDirectory, "SRA");
            throw new PlatformNotSupportedException("SRA executable is only supported on Windows and Linux.");
        }
    }

    public static string SraOldExecutablePath
    {
        get
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                return  Path.Combine(Environment.CurrentDirectory, "SRA_old.exe");
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
                return Path.Combine(Environment.CurrentDirectory, "SRA_old");
            throw new PlatformNotSupportedException("SRA old executable is only supported on Windows and Linux.");
        }
    }
    
    public static string DesktopShortcutPath
    {
        get
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "SRA.lnk");
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
            {
                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "SRA.desktop");
            }

            throw new PlatformNotSupportedException("Desktop shortcut is only supported on Windows and Linux.");
        }
    }
}
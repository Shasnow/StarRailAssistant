using System;
using System.IO;
using System.Runtime.InteropServices;

namespace SRAFrontend.Data;

public static class PathString
{
    public static readonly string AppRoot = AppContext.BaseDirectory;

    public static readonly string AppDataDir = GetAppDataDirectory();

    public static readonly string TempDir = Path.Combine(Path.GetTempPath(), "SRA");

    public static readonly string SettingsJson = Path.Combine(AppDataDir, "settings.json");
    public static readonly string CacheJson = Path.Combine(AppDataDir, "cache.json");

    public static readonly string ConfigsDir = Path.Combine(AppDataDir, "configs");
    public static readonly string FrontendLogsDir = Path.Combine(AppDataDir, "logs");
    public static readonly string BackendLogsDir = Path.Combine(AppRoot, "log");
    public static readonly string ReportsDir = Path.Combine(AppRoot, "reports");
    public static readonly string SourceCodeDir = Path.Combine(AppRoot, "SRA");
    public static readonly string StrategiesDir = Path.Combine(AppRoot, "tasks", "currency_wars", "strategies");
    public static readonly string PythonDir = GetPythonDir();

    public static readonly string SraExecutablePath = GetSraExecutablePath();
    public static readonly string SraOldExecutablePath = GetSraOldExecutablePath();
    public static readonly string DesktopShortcutPath = GetDesktopShortcutPath();
    public static string PythonExe => RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
        ? Path.Combine(PythonDir, "python.exe")
        : Path.Combine(PythonDir, "bin", "python3");

    static PathString()
    {
        EnsureDirectoryExists(AppDataDir);
        EnsureDirectoryExists(TempDir);
        EnsureDirectoryExists(ConfigsDir);
        EnsureDirectoryExists(FrontendLogsDir);
        EnsureDirectoryExists(PythonDir);
        // EnsureDirectoryExists(BackendLogsDir);
        // EnsureDirectoryExists(ReportsDir);
    }

    private static string GetAppDataDirectory()
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "SRA");

        return Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            ".config", "SRA");
    }

    private static string GetSraExecutablePath()
    {
        var exeName = RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
            ? "SRA.exe"
            : "SRA";
        return Path.Combine(AppRoot, exeName);
    }

    private static string GetSraOldExecutablePath()
    {
        var exeName = RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
            ? "SRA_old.exe"
            : "SRA_old";
        return Path.Combine(AppRoot, exeName);
    }

    private static string GetDesktopShortcutPath()
    {
        var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);

        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return Path.Combine(desktop, "SRA.lnk");

        if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
            return Path.Combine(desktop, "SRA.desktop");

        throw new PlatformNotSupportedException();
    }

    private static void EnsureDirectoryExists(string path)
    {
        if (!Directory.Exists(path))
            Directory.CreateDirectory(path);
    }

    private static string GetPythonDir()
    {
        return Path.Combine(AppRoot, "python");
    }
}
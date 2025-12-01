using System;
using System.IO;

namespace SRAFrontend.Data;

public static class PathString
{
    public static readonly string AppDataSraDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "SRA");
    public static readonly string TempSraDir = Path.Combine(Path.GetTempPath(), "SRA");
    public static readonly string SettingsJson = Path.Combine(AppDataSraDir, "settings.json");
    public static readonly string CacheJson = Path.Combine(AppDataSraDir, "cache.json");
    public static readonly string ConfigsDir = Path.Combine(AppDataSraDir, "configs");
    public static readonly string LogsDir = Path.Combine(AppDataSraDir, "logs");
    public static readonly string ReportsDir = "reports";
    // public static readonly string PythonDir = Path.Combine(Environment.CurrentDirectory, "python");
    public static readonly string SourceCodeDir = Path.Combine(Environment.CurrentDirectory, "SRA");
    public static readonly string DesktopShortcutPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "SRA.lnk");
}
using System;
using System.IO;

namespace SRAFrontend.Data;

public static class PathString
{
    public static readonly string AppDataSra = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "SRA");
    public static readonly string SettingsJson = Path.Combine(AppDataSra, "settings.json");
    public static readonly string CacheJson = Path.Combine(AppDataSra, "cache.json");
    public static readonly string ConfigsDir = Path.Combine(AppDataSra, "configs");
    public static readonly string LogsDir = Path.Combine(AppDataSra, "logs");
    public static readonly string ReportsDir = "reports";
}
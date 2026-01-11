using System.IO;
using System.Text.Json;
using SRAFrontend.Data;
using SRAFrontend.Models;

namespace SRAFrontend.Utils;

public static class DataPersister
{
    private static readonly JsonSerializerOptions JsonSerializerOptions = new()
    {
        WriteIndented = true
    };
    static DataPersister()
    {
        EnsurePath();
    }

    private static void EnsurePath()
    {
        if (!Directory.Exists(PathString.AppDataSraDir)) Directory.CreateDirectory(PathString.AppDataSraDir);
        if (!Directory.Exists(PathString.ConfigsDir)) Directory.CreateDirectory(PathString.ConfigsDir);
        // 仅创建目录，文件将在WriteAllText时创建
    }

    public static Settings LoadSettings()
    {
        if (!File.Exists(PathString.SettingsJson)) return new Settings(); 
        var json = File.ReadAllText(PathString.SettingsJson);
        if (string.IsNullOrWhiteSpace(json)) return new Settings();
        return JsonSerializer.Deserialize<Settings>(json) ?? new Settings();
    }

    public static void SaveSettings(Settings settings)
    {
        var json = JsonSerializer.Serialize(settings, JsonSerializerOptions);
        File.WriteAllText(PathString.SettingsJson, json);
    }

    public static Cache LoadCache()
    {
        if (!File.Exists(PathString.CacheJson)) return new Cache();
        var json = File.ReadAllText(PathString.CacheJson);
        if (string.IsNullOrWhiteSpace(json)) return new Cache();
        return JsonSerializer.Deserialize<Cache>(json) ?? new Cache();
    }

    public static void SaveCache(Cache cache)
    {
        var json = JsonSerializer.Serialize(cache, JsonSerializerOptions);
        File.WriteAllText(PathString.CacheJson, json);
    }

    public static Config LoadConfig(string name)
    {
        var configPath = Path.Combine(PathString.ConfigsDir, $"{name}.json");
        if (!File.Exists(configPath)) return new Config { Name = name };
        var json = File.ReadAllText(configPath);
        if (string.IsNullOrWhiteSpace(json)) return new Config { Name = name };
        var config = JsonSerializer.Deserialize<Config>(json);
        return config == null || config.Version < 3 ? new Config { Name = name } : config;
    }

    public static void SaveConfig(Config config)
    {
        var configPath = Path.Combine(PathString.ConfigsDir, $"{config.Name}.json");
        var json = JsonSerializer.Serialize(config, JsonSerializerOptions);
        File.WriteAllText(configPath, json);
    }
}
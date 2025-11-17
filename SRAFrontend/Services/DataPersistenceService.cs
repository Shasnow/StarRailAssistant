using System.IO;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class DataPersistenceService
{
    private readonly ILogger _logger;

    private readonly JsonSerializerOptions _jsonSerializerOptions = new()
    {
        WriteIndented = true
    };

    public DataPersistenceService(ILogger<DataPersistenceService> logger)
    {
        _logger = logger;
        EnsurePath();
    }

    private void EnsurePath()
    {
        if (!Directory.Exists(PathString.AppDataSra)) Directory.CreateDirectory(PathString.AppDataSra);
        if (!Directory.Exists(PathString.ConfigsDir)) Directory.CreateDirectory(PathString.ConfigsDir);
        // 仅创建目录，文件将在WriteAllText时创建
    }

    public Settings LoadSettings()
    {
        if (!File.Exists(PathString.SettingsJson)) return new Settings(); 
        var json = File.ReadAllText(PathString.SettingsJson);
        if (string.IsNullOrWhiteSpace(json)) return new Settings();
        return JsonSerializer.Deserialize<Settings>(json) ?? new Settings();
    }

    public void SaveSettings(Settings settings)
    {
        var json = JsonSerializer.Serialize(settings, _jsonSerializerOptions);
        File.WriteAllText(PathString.SettingsJson, json);
    }

    public Cache LoadCache()
    {
        if (!File.Exists(PathString.CacheJson)) return new Cache();
        var json = File.ReadAllText(PathString.CacheJson);
        if (string.IsNullOrWhiteSpace(json)) return new Cache();
        return JsonSerializer.Deserialize<Cache>(json) ?? new Cache();
    }

    public void SaveCache(Cache cache)
    {
        var json = JsonSerializer.Serialize(cache, _jsonSerializerOptions);
        File.WriteAllText(PathString.CacheJson, json);
    }

    public Config LoadConfig(string name)
    {
        _logger.LogDebug("Loading config: {name}", name);
        var configPath = Path.Combine(PathString.ConfigsDir, $"{name}.json");
        if (!File.Exists(configPath)) return new Config { Name = name };
        var json = File.ReadAllText(configPath);
        if (string.IsNullOrWhiteSpace(json)) return new Config { Name = name };
        var config = JsonSerializer.Deserialize<Config>(json);
        return config == null || config.Version < 3 ? new Config { Name = name } : config;
    }

    public void SaveConfig(Config config)
    {
        var configPath = Path.Combine(PathString.ConfigsDir, $"{config.Name}.json");
        var json = JsonSerializer.Serialize(config, _jsonSerializerOptions);
        File.WriteAllText(configPath, json);
        _logger.LogDebug("Successfully saved config: {config.Name}", config.Name);
    }
}
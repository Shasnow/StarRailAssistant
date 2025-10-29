using System;
using System.IO;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class DataPersistenceService
{
    private readonly string _baseStorageDirectory;
    private readonly string _cacheFilePath;
    private readonly string _configsDirectory;
    private readonly string _settingsFilePath;
    private readonly ILogger _logger;

    private readonly JsonSerializerOptions _jsonSerializerOptions = new()
    {
        WriteIndented = true
    };

    public DataPersistenceService(ILogger<DataPersistenceService> logger)
    {
        _logger = logger;
        _baseStorageDirectory = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "SRA");
        _settingsFilePath = Path.Combine(_baseStorageDirectory, "settings.json");
        _cacheFilePath = Path.Combine(_baseStorageDirectory, "cache.json");
        _configsDirectory = Path.Combine(_baseStorageDirectory, "configs");
        EnsurePath();
    }

    private void EnsurePath()
    {
        if (!Directory.Exists(_baseStorageDirectory)) Directory.CreateDirectory(_baseStorageDirectory);
        if (!Directory.Exists(_configsDirectory)) Directory.CreateDirectory(_configsDirectory);
        // 仅创建目录，文件将在WriteAllText时创建
    }

    public Settings LoadSettings()
    {
        EnsurePath();
        var json = File.ReadAllText(_settingsFilePath);
        if (string.IsNullOrWhiteSpace(json)) return new Settings();
        return JsonSerializer.Deserialize<Settings>(json) ?? new Settings();
    }

    public void SaveSettings(Settings settings)
    {
        EnsurePath();
        var json = JsonSerializer.Serialize(settings, _jsonSerializerOptions);
        File.WriteAllText(_settingsFilePath, json);
    }

    public Cache LoadCache()
    {
        EnsurePath();
        var json = File.ReadAllText(_cacheFilePath);
        if (string.IsNullOrWhiteSpace(json)) return new Cache();
        return JsonSerializer.Deserialize<Cache>(json) ?? new Cache();
    }

    public void SaveCache(Cache cache)
    {
        EnsurePath();
        var json = JsonSerializer.Serialize(cache, _jsonSerializerOptions);
        File.WriteAllText(_cacheFilePath, json);
    }

    public Config LoadConfig(string name)
    {
        _logger.LogDebug("Loading config: {name}", name);
        var configPath = Path.Combine(_configsDirectory, $"{name}.json");
        if (!File.Exists(configPath)) return new Config { Name = name };
        var json = File.ReadAllText(configPath);
        if (string.IsNullOrWhiteSpace(json)) return new Config { Name = name };
        var config = JsonSerializer.Deserialize<Config>(json);
        return config == null || config.Version < 3 ? new Config { Name = name } : config;
    }

    public void SaveConfig(Config config)
    {
        var configPath = Path.Combine(_configsDirectory, $"{config.Name}.json");
        var json = JsonSerializer.Serialize(config, _jsonSerializerOptions);
        File.WriteAllText(configPath, json);
        _logger.LogDebug("Successfully saved config: {config.Name}", config.Name);
    }
}
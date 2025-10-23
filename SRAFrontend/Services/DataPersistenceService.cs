using System;
using System.IO;
using System.Text.Json;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class DataPersistenceService
{
    private readonly string _baseStorageDirectory;
    private readonly string _cacheFilePath;

    private readonly JsonSerializerOptions _jsonSerializerOptions = new()
    {
        WriteIndented = true
    };

    private readonly string _settingsFilePath;

    public DataPersistenceService()
    {
        Console.Out.WriteLine("DataPersistenceService initialized.");
        _baseStorageDirectory = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "SRA");
        _settingsFilePath = Path.Combine(_baseStorageDirectory, "settings.json");
        _cacheFilePath = Path.Combine(_baseStorageDirectory, "cache.json");
        EnsurePath();
    }

    private void EnsurePath()
    {
        if (!Directory.Exists(_baseStorageDirectory)) Directory.CreateDirectory(_baseStorageDirectory);
        if (!File.Exists(_settingsFilePath)) File.Create(_settingsFilePath).Dispose();
        if (!File.Exists(_cacheFilePath)) File.Create(_cacheFilePath).Dispose();
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
}
using System;
using System.IO;
using System.Text.Json;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class DataPersistenceService
{
    private readonly string _baseStorageDirectory;

    private readonly string _settingsFilePath;
    private readonly string _cacheFilePath;
    private readonly JsonSerializerOptions _jsonSerializerOptions= new JsonSerializerOptions
    {
        WriteIndented = true
    };

    private void EnsurePath()
    {
        if (!Directory.Exists(_baseStorageDirectory)) Directory.CreateDirectory(_baseStorageDirectory);
        if (!File.Exists(_settingsFilePath)) File.Create(_settingsFilePath).Dispose();
        if (!File.Exists(_cacheFilePath)) File.Create(_cacheFilePath).Dispose();
    }

    public DataPersistenceService()
    {
        Console.Out.WriteLine("DataPersistenceService initialized.");
        _baseStorageDirectory = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "SRA");
        _settingsFilePath = Path.Combine(_baseStorageDirectory, "settings.json");
        _cacheFilePath = Path.Combine(_baseStorageDirectory, "cache.json");
        EnsurePath();
    }
    
    public Settings LoadSettings()
    {
        EnsurePath();
        var json = File.ReadAllText(_settingsFilePath);
        if (string.IsNullOrWhiteSpace(json))
        {
            return new Settings();
        }
        return JsonSerializer.Deserialize<Settings>(json) ?? new Settings();
    }
    public void SaveSettings(Settings settings)
    {
        EnsurePath();
        var json = JsonSerializer.Serialize(settings, _jsonSerializerOptions);
        File.WriteAllText(_settingsFilePath, json);
    }
}
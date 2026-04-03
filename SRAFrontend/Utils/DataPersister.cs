using System;
using System.IO;
using System.Text.Json;
using Serilog;
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
    }

    /// <summary>
    ///     原子写入文件：先写临时文件，再替换目标文件。
    ///     写入过程中崩溃不会损坏原文件。
    /// </summary>
    private static void SafeWriteAllText(string path, string content)
    {
        var dir = Path.GetDirectoryName(path)!;
        var tempPath = Path.Combine(dir, Path.GetRandomFileName());
        try
        {
            File.WriteAllText(tempPath, content);
            if (File.Exists(path))
            {
                File.Replace(tempPath, path, null);
            }
            else
            {
                File.Move(tempPath, path);
            }
        }
        catch
        {
            if (File.Exists(tempPath)) File.Delete(tempPath);
            throw;
        }
    }

    #region Settings

    public static Settings LoadSettings()
    {
        try
        {
            if (!File.Exists(PathString.SettingsJson)) return new Settings();
            var json = File.ReadAllText(PathString.SettingsJson);
            if (string.IsNullOrWhiteSpace(json)) return new Settings();
            return JsonSerializer.Deserialize<Settings>(json) ?? new Settings();
        }
        catch (Exception e)
        {
            Log.Error(e, "Error loading settings, using default settings");
            return new Settings();
        }
        
    }

    public static void SaveSettings(Settings settings)
    {
        var json = JsonSerializer.Serialize(settings, JsonSerializerOptions);
        SafeWriteAllText(PathString.SettingsJson, json);
    }

    #endregion

    #region Cache

    public static Cache LoadCache()
    {
        try
        {
            if (!File.Exists(PathString.CacheJson)) return new Cache();
            var json = File.ReadAllText(PathString.CacheJson);
            if (string.IsNullOrWhiteSpace(json)) return new Cache();
            return JsonSerializer.Deserialize<Cache>(json) ?? new Cache();
        }
        catch (Exception e)
        {
            Log.Error(e, "Error loading cache. using empty cache");
            return new Cache();
        }
    }

    public static void SaveCache(Cache cache)
    {
        var json = JsonSerializer.Serialize(cache, JsonSerializerOptions);
        SafeWriteAllText(PathString.CacheJson, json);
    }

    #endregion

    #region Config

    public static Config LoadConfig(string name)
    {
        try
        {
            var configPath = Path.Combine(PathString.ConfigsDir, $"{name}.json");
            if (!File.Exists(configPath)) return new Config { Name = name };
            var json = File.ReadAllText(configPath);
            if (string.IsNullOrWhiteSpace(json)) return new Config { Name = name };
            var config = JsonSerializer.Deserialize<Config>(json);
            return config == null || config.Version < Config.StaticVersion ? new Config { Name = name } : config;
        }
        catch (Exception e)
        {
            Log.Error(e, "Error loading config {ConfigName}, using default config", name);
            return new Config { Name = name };
        }

    }

    public static void SaveConfig(Config config)
    {
        var configPath = Path.Combine(PathString.ConfigsDir, $"{config.Name}.json");
        var json = JsonSerializer.Serialize(config, JsonSerializerOptions);
        SafeWriteAllText(configPath, json);
    }

    #endregion
}

using System.IO;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Utils;

namespace SRAFrontend.Services;

public class ConfigService(CacheService cacheService, ILogger<ConfigService> logger)
{
    private readonly JsonSerializerOptions _jsonSerializerOptions = new() { WriteIndented = true };

    public TasksConfig? TaskConfig { get; private set; }

    public void Load()
    {
        var configName = cacheService.Cache.CurrentConfigName;
        Load(configName);
    }

    private void Load(string configName)
    {
        logger.LogInformation("Loading config: {ConfigName}", configName);
        var configPath = Path.Combine(PathString.ConfigsDir, $"{configName}.json");
        if (!File.Exists(configPath))
        {
            logger.LogWarning("Config file not found: {ConfigPath}, use default config", configPath);
            TaskConfig = new TasksConfig { Name = configName };
            return;
        }

        var configJson = File.ReadAllText(configPath);
        var config = JsonSerializer.Deserialize<TasksConfig>(configJson)!;
        if (config.Version < TasksConfig.StaticVersion)
        {
            logger.LogWarning("Config version {Version} is deprecated. Use default config instead", config.Version);
            TaskConfig = new TasksConfig { Name = configName };
            return;
        }

        TaskConfig = config;
        TaskConfig.Name = configName;
        DecryptSensitiveFields();
    }

    public void Save()
    {
        logger.LogInformation("Saving config: {ConfigName}", TaskConfig?.Name);
        EncryptSensitiveFields();
        var configJson = JsonSerializer.Serialize(TaskConfig, _jsonSerializerOptions);
        File.WriteAllText(Path.Combine(PathString.ConfigsDir, $"{TaskConfig?.Name}.json"), configJson);
    }

    private void EncryptSensitiveFields()
    {
        if (TaskConfig is null) return;
        TaskConfig.StartGame.EncryptedUsername = EncryptUtil.EncryptString(TaskConfig.StartGame.Username);
        TaskConfig.StartGame.EncryptedPassword = EncryptUtil.EncryptString(TaskConfig.StartGame.Password);
    }

    private void DecryptSensitiveFields()
    {
        if (TaskConfig is null) return;
        TaskConfig.StartGame.Username = EncryptUtil.DecryptString(TaskConfig.StartGame.EncryptedUsername);
        TaskConfig.StartGame.Password = EncryptUtil.DecryptString(TaskConfig.StartGame.EncryptedPassword);
    }

    public void SwitchConfig(string configName)
    {
        Save();
        Load(configName);
        cacheService.Cache.CurrentConfigName = configName;
    }
}
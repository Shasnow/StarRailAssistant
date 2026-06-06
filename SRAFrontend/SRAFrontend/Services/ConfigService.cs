using System;
using System.IO;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Migrations;
using SRAFrontend.Models;
using SRAFrontend.Utils;

namespace SRAFrontend.Services;

public class ConfigService(CacheService cacheService, ILogger<ConfigService> logger)
{
    private readonly JsonSerializerOptions _jsonSerializerOptions = new() { WriteIndented = true };

    public TasksConfig? TasksConfig { get; private set; }

    public void Load()
    {
        var configName = cacheService.Cache.CurrentConfigName;
        Load(configName);
    }

    public void Load(string configName)
    {
        if (string.IsNullOrWhiteSpace(configName))
            configName = "Default";

        logger.LogInformation("Loading config: {ConfigName}", configName);
        var configPath = Path.Combine(DataPath.ConfigsDir, $"{configName}.json");

        // 不存在 → 新建
        if (!File.Exists(configPath))
        {
            logger.LogWarning("Config file not found, creating default: {ConfigName}", configName);
            TasksConfig = new TasksConfig { Name = configName };
            return;
        }

        try
        {
            var configJson = File.ReadAllText(configPath);
            TasksConfig? newConfig = null;

            // 旧格式迁移
            if (configJson.Contains("AfterExitApp"))
            {
                logger.LogInformation("Migrating OLD config format...");
                var oldConfig = JsonSerializer.Deserialize<Config>(configJson);
                if (oldConfig != null)
                {
                    newConfig = ConfigMigrator.MigrateOldToNew(oldConfig);
                }
            }
            else
            {
                newConfig = JsonSerializer.Deserialize<TasksConfig>(configJson);
            }

            // 加载失败 / 版本过低 → 使用默认
            if (newConfig == null || newConfig.Version < TasksConfig.StaticVersion)
            {
                if (newConfig != null)
                    logger.LogWarning("Config version deprecated, using default");

                newConfig = new TasksConfig { Version = TasksConfig.StaticVersion };
            }

            newConfig.Name = configName;
            TasksConfig = newConfig;

            DecryptSensitiveFields();
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load config, using default");
            TasksConfig = new TasksConfig { Name = configName, Version = TasksConfig.StaticVersion };
        }
    }

    public void Save()
    {
        logger.LogInformation("Saving config: {ConfigName}", TasksConfig?.Name);
        EncryptSensitiveFields();
        var configJson = JsonSerializer.Serialize(TasksConfig, _jsonSerializerOptions);
        File.WriteAllText(Path.Combine(DataPath.ConfigsDir, $"{TasksConfig?.Name}.json"), configJson);
    }

    private void EncryptSensitiveFields()
    {
        if (TasksConfig is null) return;
        TasksConfig.StartGame.EncryptedUsername = EncryptUtil.EncryptString(TasksConfig.StartGame.Username);
        TasksConfig.StartGame.EncryptedPassword = EncryptUtil.EncryptString(TasksConfig.StartGame.Password);
    }

    private void DecryptSensitiveFields()
    {
        if (TasksConfig is null) return;
        TasksConfig.StartGame.Username = EncryptUtil.DecryptString(TasksConfig.StartGame.EncryptedUsername);
        TasksConfig.StartGame.Password = EncryptUtil.DecryptString(TasksConfig.StartGame.EncryptedPassword);
    }

    public void SwitchConfig(string configName)
    {
        Save();
        Load(configName);
        cacheService.Cache.CurrentConfigName = configName;
    }
}
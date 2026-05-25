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

    public TasksConfig? TaskConfig { get; private set; }

    public void Load()
    {
        var configName = cacheService.Cache.CurrentConfigName;
        Load(configName);
    }

    private void Load(string configName)
    {
        if (string.IsNullOrWhiteSpace(configName))
            configName = "Default";

        logger.LogInformation("Loading config: {ConfigName}", configName);
        var configPath = Path.Combine(PathString.ConfigsDir, $"{configName}.json");

        // 不存在 → 新建
        if (!File.Exists(configPath))
        {
            logger.LogWarning("Config file not found, creating default: {ConfigName}", configName);
            TaskConfig = new TasksConfig { Name = configName };
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
            TaskConfig = newConfig;

            DecryptSensitiveFields();
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load config, using default");
            TaskConfig = new TasksConfig { Name = configName, Version = TasksConfig.StaticVersion };
        }
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
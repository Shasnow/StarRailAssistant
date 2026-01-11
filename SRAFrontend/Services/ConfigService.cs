using System;
using Microsoft.Extensions.Logging;
using SRAFrontend.Models;
using SRAFrontend.Utils;

namespace SRAFrontend.Services;

public class ConfigService
{
    private readonly CacheService _cacheService;
    private readonly ILogger<ConfigService> _logger;

    public ConfigService(CacheService cacheService, ILogger<ConfigService> logger)
    {
        _cacheService = cacheService;
        _logger = logger;
        var currentConfigName = _cacheService.Cache.CurrentConfigName;
        LoadConfig(currentConfigName);
    }

    public Config? Config { get; private set; }

    public void SaveConfig()
    {
        _logger.LogInformation("Saving config");
        if (Config is null) throw new InvalidOperationException("Config is null");
        if (!string.IsNullOrEmpty(Config.StartGamePassword))
            try
            {
                Config.EncryptedStartGamePassword = EncryptUtil.EncryptString(Config.StartGamePassword);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Failed to encrypt StartGamePassword");
                Config.EncryptedStartGamePassword = "";
            }

        if (!string.IsNullOrEmpty(Config.StartGameUsername))
            try
            {
                Config.EncryptedStartGameUsername = EncryptUtil.EncryptString(Config.StartGameUsername);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Failed to encrypt StartGameUsername");
                Config.EncryptedStartGameUsername = "";
            }

        DataPersister.SaveConfig(Config);
    }

    private void LoadConfig(string configName)
    {
        _logger.LogInformation("Loading config: {ConfigName}", configName);
        Config = DataPersister.LoadConfig(configName);
        if (!string.IsNullOrEmpty(Config.EncryptedStartGamePassword))
            try
            {
                Config.StartGamePassword = EncryptUtil.DecryptString(Config.EncryptedStartGamePassword);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Failed to decrypt StartGamePassword");
                Config.StartGamePassword = "";
            }

        if (!string.IsNullOrEmpty(Config.EncryptedStartGameUsername))
            try
            {
                Config.StartGameUsername = EncryptUtil.DecryptString(Config.EncryptedStartGameUsername);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Failed to decrypt StartGameUsername");
                Config.StartGameUsername = "";
            }
    }

    public void SwitchConfig(string configName)
    {
        SaveConfig();
        LoadConfig(configName);
        _cacheService.Cache.CurrentConfigName = configName;
    }
}
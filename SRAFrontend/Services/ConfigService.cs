using System;
using SRAFrontend.Models;
using SRAFrontend.utilities;

namespace SRAFrontend.Services;

public class ConfigService
{
    public Config? Config{get; private set;}
    private readonly DataPersistenceService _dataPersistenceService;
    private readonly CacheService _cacheService;

    public ConfigService(DataPersistenceService dataPersistenceService, CacheService cacheService)
    {
        _dataPersistenceService = dataPersistenceService;
        _cacheService = cacheService;
        var currentConfigName = _cacheService.Cache.CurrentConfigName;
        LoadConfig(currentConfigName);
    }

    public void SaveConfig()
    {
        if (Config is null) throw new InvalidOperationException("Config is null");
        Config.EncryptedStartGamePassword = string.IsNullOrEmpty(Config.StartGamePassword) ? "" : EncryptUtil.EncryptString(Config.StartGamePassword);
        Config.EncryptedStartGameUsername = string.IsNullOrEmpty(Config.StartGameUsername) ? "" : EncryptUtil.EncryptString(Config.StartGameUsername);
        _dataPersistenceService.SaveConfig(Config);
    }
    private void LoadConfig(string configName)
    {
        Config = _dataPersistenceService.LoadConfig(configName);
        if(!string.IsNullOrEmpty(Config.EncryptedStartGamePassword))
            Config.StartGamePassword = EncryptUtil.DecryptString(Config.EncryptedStartGamePassword);
        if(!string.IsNullOrEmpty(Config.EncryptedStartGameUsername))
            Config.StartGameUsername = EncryptUtil.DecryptString(Config.EncryptedStartGameUsername);
    }
    public void SwitchConfig(string configName)
    {
        SaveConfig();
        LoadConfig(configName);
        _cacheService.Cache.CurrentConfigName = configName;
    }
}
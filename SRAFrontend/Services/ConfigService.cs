using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class ConfigService
{
    public Config Config{get; private set;}
    private readonly DataPersistenceService _dataPersistenceService;
    private readonly CacheService _cacheService;

    public ConfigService(DataPersistenceService dataPersistenceService, CacheService cacheService)
    {
        _dataPersistenceService = dataPersistenceService;
        _cacheService = cacheService;
        var currentConfigName = _cacheService.Cache.CurrentConfigName;
        Config = dataPersistenceService.LoadConfig(currentConfigName);
    }

    public void SaveConfig()
    {
        _dataPersistenceService.SaveConfig(Config);
    }
    
    public void SwitchConfig(string configName)
    {
        SaveConfig();
        Config = _dataPersistenceService.LoadConfig(configName);
        _cacheService.Cache.CurrentConfigName = configName;
    }
}
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class CacheService(DataPersistenceService dataPersistenceService)
{
    public readonly Cache Cache = dataPersistenceService.LoadCache();

    public void SaveCache()
    {
        dataPersistenceService.SaveCache(Cache);
    }
}
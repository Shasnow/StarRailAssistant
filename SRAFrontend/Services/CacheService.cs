using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class CacheService(DataPersistenceService dataPersistenceService)
{
    public Cache Cache { get; } = dataPersistenceService.LoadCache();

    public void SaveCache()
    {
        dataPersistenceService.SaveCache(Cache);
    }
}
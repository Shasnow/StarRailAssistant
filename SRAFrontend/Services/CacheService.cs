using SRAFrontend.Models;
using SRAFrontend.Utils;

namespace SRAFrontend.Services;

public class CacheService
{
    public Cache Cache { get; } = DataPersister.LoadCache();

    public void SaveCache()
    {
        DataPersister.SaveCache(Cache);
    }
}
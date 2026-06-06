using System;
using Microsoft.Extensions.Logging;
using SRAFrontend.Models;
using SRAFrontend.Utils;

namespace SRAFrontend.Services;

public class CacheService(ILogger<CacheService> logger)
{
    public Cache Cache { get; private set; } = new();

    public void Load()
    {
        logger.LogInformation("Loading cache...");
        Cache = DataPersister.LoadCache();
        Cache.LastLaunchTimestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
    }

    public void SaveCache()
    {
        logger.LogInformation("Saving cache...");
        DataPersister.SaveCache(Cache);
    }
}

using System;
using SRAFrontend.Models;
using SRAFrontend.Utils;

namespace SRAFrontend.Services;

public class CacheService
{
    public CacheService()
    {
        Cache = DataPersister.LoadCache();
        Cache.LastLaunchTimestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(); // 记录当前启动时间戳
    }

    public Cache Cache { get; }

    public void SaveCache()
    {
        DataPersister.SaveCache(Cache);
    }
}
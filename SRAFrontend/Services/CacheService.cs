using System;
using SRAFrontend.Models;
using SRAFrontend.Utils;

namespace SRAFrontend.Services;

public class CacheService
{
    public CacheService()
    {
        Cache = DataPersister.LoadCache();
        if (string.IsNullOrEmpty(Cache.DeviceId)) Cache.DeviceId = Guid.NewGuid().ToString(); // 生成新的设备ID
        Cache.LastLaunchTimestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(); // 记录当前启动时间戳
    }

    public Cache Cache { get; }

    public void SaveCache()
    {
        DataPersister.SaveCache(Cache);
    }
}
using System;
using System.IO;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class ReportService(
    IHttpClientFactory httpClientFactory,
    CacheService cacheService,
    ILogger<ReportService> logger)
{
    private const string ReportUrl = "https://shasnow.top/api/report";
    private string? _deviceIdCache;

    private string GetDeviceId()
    {
        if (!string.IsNullOrEmpty(_deviceIdCache)) return _deviceIdCache;
        var deviceIdFilePath = Path.Combine(PathString.AppDataSraDir, "profile.txt");
        if (File.Exists(deviceIdFilePath))
        {
            _deviceIdCache = File.ReadAllText(deviceIdFilePath).Trim();
            if (!string.IsNullOrEmpty(_deviceIdCache)) return _deviceIdCache;
        }
        _deviceIdCache = Guid.NewGuid().ToString();
        File.WriteAllText(deviceIdFilePath, _deviceIdCache);
        return _deviceIdCache;
    }
    
    private AppEvent CreateAppEvent(string eventType, string? eventData)
    {
        var deviceId = GetDeviceId();
        var timestampNow = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        return new AppEvent
        {
            DeviceId = deviceId,
            EventType = eventType,
            EventData = eventData,
            AppId = "SRA",
            AppVersion = Settings.Version,
            Timestamp = timestampNow,
            SessionDuration = timestampNow - cacheService.Cache.LastLaunchTimestamp,
        };
    }
    
    public async Task<bool> ReportAsync(string eventType, string? eventData)
    {
        logger.LogInformation("Start report event {EventType}.", eventType);
        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        try
        {
            var appEvent = CreateAppEvent(eventType, eventData);
            var response = await httpClient.PostAsJsonAsync(ReportUrl, appEvent);
            response.EnsureSuccessStatusCode();
            logger.LogInformation("Reported event {EventType} successfully.", eventType);
            return true;
        }
        catch (Exception)
        {
            logger.LogError("Failed to report event async {EventType}.", eventType);
            return false;
        }
    }

    public void Report(string eventType, string? eventData, int timeoutMs = 1000)
    {
        try
        {
            logger.LogInformation("Start report event {EventType}", eventType);
            var httpClient = httpClientFactory.CreateClient("GlobalClient");
            httpClient.Timeout = TimeSpan.FromMilliseconds(timeoutMs);
        
            var appEvent = CreateAppEvent(eventType, eventData);
            var response = httpClient.PostAsJsonAsync(ReportUrl, appEvent).Result;
            response.EnsureSuccessStatusCode();
            logger.LogInformation("Reported event {EventType} successfully.", eventType);
        }
        catch (AggregateException ex)
        {
            // 捕获Result的聚合异常，解析实际错误
            var innerEx = ex.InnerException ?? ex;
            logger.LogError(innerEx, "Failed to report event {EventType}, inner error: {Msg}", 
                eventType, innerEx.Message);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to report event {EventType}.", eventType);
        }
    }
}
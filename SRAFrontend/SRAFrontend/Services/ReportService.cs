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
    private const string ReportUrl = "https://shasnow.top/s/api/report";
    private string? _deviceIdCache;

    public string GetDeviceId()
    {
        if (!string.IsNullOrEmpty(_deviceIdCache)) return _deviceIdCache;
        var deviceIdFilePath = Path.Combine(DataPath.AppDataDir, "profile.txt");
        if (File.Exists(deviceIdFilePath))
        {
            _deviceIdCache = File.ReadAllText(deviceIdFilePath).Trim();
            if (!string.IsNullOrEmpty(_deviceIdCache)) return _deviceIdCache;
        }

        _deviceIdCache = Guid.NewGuid().ToString();
        File.WriteAllText(deviceIdFilePath, _deviceIdCache);
        return _deviceIdCache;
    }

    private AppEvent CreateAppEvent(string eventType, string eventData)
    {
        var deviceId = GetDeviceId();
        var timestampNow = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        return new AppEvent
        {
            DeviceId = deviceId,
            EventType = eventType,
            EventData = eventData,
            AppId = "SRA",
            AppVersion = AppSettings.Version,
            Timestamp = timestampNow,
            SessionDuration = timestampNow - cacheService.Cache.LastLaunchTimestamp
        };
    }

    public async Task<bool> ReportAsync(string eventType, string eventData)
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

    public void Report(string eventType, string eventData, int timeoutMs = 5000)
    {
        try
        {
            logger.LogInformation("Start report event {EventType}", eventType);
            var httpClient = httpClientFactory.CreateClient("GlobalClient");
            httpClient.Timeout = TimeSpan.FromMilliseconds(timeoutMs);

            var appEvent = CreateAppEvent(eventType, eventData);
            var response = httpClient.PostAsJsonAsync(ReportUrl, appEvent).GetAwaiter().GetResult();
            response.EnsureSuccessStatusCode();
            logger.LogInformation("Reported event {EventType} successfully.", eventType);
        }
        catch (TaskCanceledException ex)
        {
            // 程序退出或超时导致请求被取消，属于上报的预期内失败，不输出堆栈
            logger.LogWarning("Report event {EventType} canceled or timed out: {Message}",
                eventType, ex.Message);
        }
        catch (HttpRequestException ex)
        {
            // 网络不可用等连接问题同样只记录简要信息
            logger.LogWarning("Failed to report event {EventType}: {Message}", eventType, ex.Message);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to report event {EventType}.", eventType);
        }
    }
}
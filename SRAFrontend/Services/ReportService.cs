using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class ReportService(
    IHttpClientFactory httpClientFactory,
    CacheService cacheService,
    ILogger<ReportService> logger)
{
    private const string ReportUrl = "https://shasnow.top/api/report";

    public async Task<bool> ReportAsync(string eventType, string? eventData)
    {
        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        var deviceId = cacheService.Cache.DeviceId;
        var timestampNow = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        var appEvent = new AppEvent
        {
            DeviceId = deviceId,
            EventType = eventType,
            EventData = eventData,
            AppId = "SRA",
            AppVersion = Settings.Version,
            Timestamp = timestampNow,
            SessionDuration = timestampNow - cacheService.Cache.LastLaunchTimestamp,
        };
        try
        {
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
            var reportTask = ReportAsync(eventType, eventData);
            if (!reportTask.Wait(timeoutMs)) logger.LogWarning("Reporting event {EventType} timed out.", eventType);
        }
        catch (Exception )
        {
            logger.LogError("Failed to report event {EventType}.", eventType);
        }
    }
}
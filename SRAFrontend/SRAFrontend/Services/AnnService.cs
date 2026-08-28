using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class AnnService(IHttpClientFactory httpClientFactory, ILogger<AnnService> logger)
{
    private const string RequestUrl = "https://starrailassistant.top/api/v1/anno.json";
    public AnnouncementList? CachedAnnouncements { get; private set; } // 缓存数据，避免重复请求

    /// <summary>
    ///     获取公告列表（带缓存）
    /// </summary>
    public async Task<AnnouncementList?> GetAnnouncementsAsync()
    {
        try
        {
            var httpClient = httpClientFactory.CreateClient("GlobalClient");
            CachedAnnouncements = await httpClient.GetFromJsonAsync<AnnouncementList>(RequestUrl);
            return CachedAnnouncements;
        }
        catch (HttpRequestException ex)
        {
            logger.LogError("HTTP Request Error while fetching announcements: {Message}", ex.Message);
            return null;
        }
        catch (JsonException ex)
        {
            logger.LogError("JSON Error while fetching announcements: {Message}", ex.Message);
            return null;
        }
    }
    
    public async Task<bool> HasNewAnnouncementsAsync(int lastKnownId)
    {
        var announcements = await GetAnnouncementsAsync();
        if (announcements == null)
        {
            logger.LogWarning("Failed to fetch announcements for new check.");
            return false; // 请求失败，无法判断
        }

        return announcements.Id > lastKnownId;
    }

    public int LatestAnnouncementId => CachedAnnouncements?.Id ?? 0;
    
    /// <summary>
    ///     强制刷新缓存（重新请求数据）
    /// </summary>
    public async Task<AnnouncementList?> RefreshAnnouncementsAsync()
    {
        CachedAnnouncements = null; // 清空缓存
        return await GetAnnouncementsAsync(); // 重新获取
    }

    public ReadOnlySpan<char> BuildAnnouncementHtml(AnnouncementList announcementList)
    {
        
        var htmlBuilder = new System.Text.StringBuilder();
        htmlBuilder.AppendLine("<html><head><meta charset=\"UTF-8\"></head><body>");
        foreach (var announcement in announcementList.Announcements)
        {
            htmlBuilder.AppendLine($"<h2>{announcement.Title}</h2>");
            htmlBuilder.AppendLine($"<p>{announcement.Content}</p>");
        }
        htmlBuilder.AppendLine("</body></html>");
        return htmlBuilder.ToString().AsSpan();
    }
}
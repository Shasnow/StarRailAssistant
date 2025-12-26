using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class AnnouncementService(IHttpClientFactory httpClientFactory, ILogger<AnnouncementService> logger)
{
    private List<Announcement>? _cachedAnnouncements; // 缓存数据，避免重复请求

    private const string RequestUrl = "https://gitee.com/yukikage/sraresource/raw/main/SRA/announcements.json";

    /// <summary>
    /// 获取公告列表（带缓存）
    /// </summary>
    public async Task<List<Announcement>?> GetAnnouncementsAsync()
    {
        // 如果已有缓存，直接返回
        if (_cachedAnnouncements != null)
            return _cachedAnnouncements;

        try
        {
            var httpClient = httpClientFactory.CreateClient("GlobalClient");
            _cachedAnnouncements = await httpClient.GetFromJsonAsync<List<Announcement>>(RequestUrl);
            return _cachedAnnouncements;
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

    /// <summary>
    /// 强制刷新缓存（重新请求数据）
    /// </summary>
    public async Task<List<Announcement>?> RefreshAnnouncementsAsync()
    {
        _cachedAnnouncements = null; // 清空缓存
        return await GetAnnouncementsAsync(); // 重新获取
    }
}
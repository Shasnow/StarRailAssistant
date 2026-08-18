using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class ActivityService(IHttpClientFactory httpClientFactory, ILogger<ActivityService> logger)
{
    private const string RequestUrl = "https://starrailassistant.top/api/v1/activity/sr.json";

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    public async Task<GameVersionInfo?> GetVersionActivitiesAsync()
    {
        try
        {
            var httpClient = httpClientFactory.CreateClient("GlobalClient");
            return await httpClient.GetFromJsonAsync<GameVersionInfo>(RequestUrl, JsonOptions);
        }
        catch (HttpRequestException ex)
        {
            logger.LogError("HTTP Request Error while fetching activities: {Message}", ex.Message);
            return null;
        }
        catch (JsonException ex)
        {
            logger.LogError("JSON Error while fetching activities: {Message}", ex.Message);
            return null;
        }
    }
}

using System.Text.Json.Serialization;

namespace SRAFrontend.Models;

public class AppEvent
{
    [JsonPropertyName("deviceId")]
    public string DeviceId { get; set; } = string.Empty;
    [JsonPropertyName("eventType")]
    public string EventType { get; set; } = string.Empty;
    [JsonPropertyName("eventData")]
    public string? EventData { get; set; }
    [JsonPropertyName("appId")]
    public string AppId { get; set; } = string.Empty;
    [JsonPropertyName("appVersion")]
    public string AppVersion { get; set; } = string.Empty;
    [JsonPropertyName("timestamp")]
    public long Timestamp { get; set; }
    [JsonPropertyName("sessionDuration")]
    public long SessionDuration { get; set; }
}
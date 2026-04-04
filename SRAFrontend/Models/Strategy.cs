using System.Text.Json.Serialization;

namespace SRAFrontend.Models;

public class Strategy
{
    public string FileName { get; set; } = "";
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";
    [JsonPropertyName("title")]
    public string Title { get; set; } = "";
}
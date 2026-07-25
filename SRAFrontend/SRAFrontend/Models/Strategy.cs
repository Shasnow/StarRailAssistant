using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace SRAFrontend.Models;

public class Strategy
{
    [JsonPropertyName("file")]
    public string FileName { get; set; } = "";
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";
    [JsonPropertyName("title")]
    public string Title { get; set; } = "";
    [JsonPropertyName("author")]
    public string Author { get; set; } = "";
    [JsonPropertyName("description")]
    public string Description { get; set; } = "";
    [JsonPropertyName("min_coins")]
    public int MinCoins { get; set; }
    [JsonPropertyName("min_level")]
    public int MinLevel { get; set; }
    [JsonPropertyName("on_field")]
    public Dictionary<string, int> OnField { get; set; } = new();
    [JsonPropertyName("off_field")]
    public Dictionary<string, int> OffField { get; set; } = new();
}
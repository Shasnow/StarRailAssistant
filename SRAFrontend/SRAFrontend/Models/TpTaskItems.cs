using System.Text.Json.Serialization;

namespace SRAFrontend.Models;
public sealed record TpTask(
    [property: JsonPropertyName("func")] string Id,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("levels")] TpTaskLevel[] Levels,
    [property: JsonPropertyName("cost")] int Cost,
    [property: JsonPropertyName("max_count")] int MaxSingleTimes);

public record TpTaskLevel(
    [property: JsonPropertyName("id")] int Id,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("result")] string Result);
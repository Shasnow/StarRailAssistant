using System.Text.Json.Serialization;

namespace SRAFrontend.Models;

public class CosmicStrifePolicyState
{
    [JsonPropertyName("du")] public ModuleRunCounters Du { get; set; } = new();
    [JsonPropertyName("cw")] public ModuleRunCounters Cw { get; set; } = new();
}

public class ModuleRunCounters
{
    [JsonPropertyName("daily_date")] public string DailyDate { get; set; } = "";
    [JsonPropertyName("daily_runs")] public int DailyRuns { get; set; }
    [JsonPropertyName("week_key")] public string WeekKey { get; set; } = "";
    [JsonPropertyName("weekly_runs")] public int WeeklyRuns { get; set; }
}


using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace SRAFrontend.Models;

public class RuntimeTaskSession
{
    [JsonPropertyName("schemaVersion")] public int SchemaVersion { get; set; }
    [JsonPropertyName("sessionId")] public string SessionId { get; set; } = "";
    [JsonPropertyName("pid")] public int Pid { get; set; }
    [JsonPropertyName("owner")] public string Owner { get; set; } = "";
    [JsonPropertyName("mode")] public string Mode { get; set; } = "";
    [JsonPropertyName("configNames")] public List<string> ConfigNames { get; set; } = [];
    [JsonPropertyName("taskName")] public string? TaskName { get; set; }
    [JsonPropertyName("state")] public string State { get; set; } = "";
    [JsonPropertyName("startedAt")] public string StartedAt { get; set; } = "";
    [JsonPropertyName("startedAtUnix")] public double StartedAtUnix { get; set; }
    [JsonPropertyName("lastHeartbeat")] public string LastHeartbeat { get; set; } = "";
    [JsonPropertyName("lastHeartbeatUnix")] public double LastHeartbeatUnix { get; set; }
}

public class RuntimeTaskStatus
{
    public bool Running { get; set; }
    public int? Pid { get; set; }
    public string? SessionId { get; set; }
    public string State { get; set; } = "idle";
    public string Owner { get; set; } = "";
    public string Mode { get; set; } = "";
    public string? TaskName { get; set; }
    public IReadOnlyList<string> ConfigNames { get; set; } = [];
    public DateTimeOffset? StartedAt { get; set; }
    public DateTimeOffset? LastHeartbeat { get; set; }
    public string Detail { get; set; } = "";
}

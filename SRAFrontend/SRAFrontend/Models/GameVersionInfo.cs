namespace SRAFrontend.Models;

public record GameVersionInfo
{
    public string Version { get; set; } = string.Empty;
    public string VersionName { get; set; } = string.Empty;
    public string StartTime { get; set; } = string.Empty;
    public string EndTime { get; set; } = string.Empty;
    public GameActivityInfo[]? Activities { get; set; }
}

public record GameActivityInfo
{
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string StartTime { get; set; } = string.Empty;
    public string EndTime { get; set; } = string.Empty;
}
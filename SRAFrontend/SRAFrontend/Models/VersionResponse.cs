using System.Text.Json.Serialization;

namespace SRAFrontend.Models;

public class VersionResponse
{
    /// <summary>版本响应体模型</summary>
    public int Code { get; init; }

    public string Msg { get; init; } = "";
    
    public string Message { get; init; } = "";

    public VersionResponseData Data { get; set; } =new();
}

public class VersionResponseData
{
    /// <summary>版本响应数据模型</summary>
    public string VersionName { get; set; } = "";

    public int VersionNumber { get; set; } = 0;

    public string Url { get; set; } = "";

    public string? Sha256 { get; set; }

    public string Channel { get; set; } = "";

    public string Os { get; set; } = "";

    public string Arch { get; set; } = "";

    public string UpdateType { get; set; } = "";

    public int Filesize { get; set; } = 0;

    public int CdkExpiredTime { get; set; } = 0;

    public string ReleaseNote { get; set; } = "";
    
    public PublishedVersion? PublishedVersion { get; set; }
}

public record PublishedVersion(string SourceFilename, string Sha256);
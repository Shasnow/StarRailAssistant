using System.Text.Json.Serialization;

namespace SRAFrontend.Models;

public class VersionResponse
{
    /// <summary>版本响应体模型</summary>
    [JsonPropertyName("code")]
    public int Code { get; init; }

    [JsonPropertyName("msg")]
    public string Msg { get; init; } = "";

    [JsonPropertyName("data")]
    public VersionResponseData? Data { get; init; }
}

public class VersionResponseData
{
    /// <summary>版本响应数据模型</summary>
    [JsonPropertyName("version_name")]
    public string VersionName { get; set; } = "";

    [JsonPropertyName("version_number")]
    public int VersionNumber { get; set; } = 0;

    [JsonPropertyName("url")]
    public string Url { get; set; } = "";

    [JsonPropertyName("sha256")]
    public string Sha256 { get; set; } = "";

    [JsonPropertyName("channel")]
    public string Channel { get; set; } = "";

    [JsonPropertyName("os")]
    public string Os { get; set; } = "";

    [JsonPropertyName("arch")]
    public string Arch { get; set; } = "";

    [JsonPropertyName("update_type")]
    public string UpdateType { get; set; } = "";

    [JsonPropertyName("filesize")]
    public int Filesize { get; set; } = 0;

    [JsonPropertyName("cdk_expired_time")]
    public int CdkExpiredTime { get; set; } = 0;

    [JsonPropertyName("release_note")]
    public string ReleaseNote { get; set; } = "";
}
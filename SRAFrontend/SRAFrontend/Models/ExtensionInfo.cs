using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace SRAFrontend.Models;

public class ExtensionInfo
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";
    [JsonPropertyName("description")]
    public string Description { get; set; } = "";
    [JsonPropertyName("extension_class")]
    public string ExtensionClass { get; set; } = "";
    [JsonPropertyName("config_class")]
    public string ConfigClass { get; set; } = "";
}

/// <summary>
/// JSON Schema 中的单个属性定义，用于动态渲染表单。
/// </summary>
public class ExtensionSchemaProperty
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = "";
    [JsonPropertyName("description")]
    public string Description { get; set; } = "";
    [JsonPropertyName("default")]
    public JsonElement? Default { get; set; }
    [JsonPropertyName("minimum")]
    public decimal? Minimum { get; set; }
    [JsonPropertyName("maximum")]
    public decimal? Maximum { get; set; }
}

/// <summary>
/// 扩展配置的 JSON Schema，从 extension info --json 获取。
/// </summary>
public class ExtensionSchema
{
    [JsonPropertyName("properties")]
    public Dictionary<string, ExtensionSchemaProperty> Properties { get; set; } = new();
}

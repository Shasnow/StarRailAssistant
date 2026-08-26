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
    public string Type { get; set; } = "";
    public string Description { get; set; } = "";
    public JsonElement? Default { get; set; }
    public decimal? Minimum { get; set; }
    public decimal? Maximum { get; set; }
}

/// <summary>
/// 扩展配置的 JSON Schema，从 extension schema --json 获取。
/// </summary>
public class ExtensionSchema
{
    public string Title { get; set; } = "";
    public string Description { get; set; } = "";
    public string Type { get; set; } = "object";
    public Dictionary<string, ExtensionSchemaProperty> Properties { get; set; } = new();
}

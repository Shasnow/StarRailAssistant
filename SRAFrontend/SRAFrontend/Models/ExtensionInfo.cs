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
    /// <summary>是否包含执行逻辑；false 时只提供启用/禁用。</summary>
    [JsonPropertyName("executable")]
    public bool Executable { get; set; } = true;
    /// <summary>无执行逻辑扩展的启用状态；配置中没有 enabled 字段时为 null。</summary>
    [JsonPropertyName("enabled")]
    public bool? Enabled { get; set; }
    /// <summary>扩展目录下的 README.md 内容；没有文档时为空串。</summary>
    [JsonPropertyName("readme")]
    public string Readme { get; set; } = "";
}

/// <summary>
/// JSON Schema 中的单个属性定义，用于动态渲染表单。
/// </summary>
public class ExtensionSchemaProperty
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = "";
    [JsonPropertyName("title")]
    public string Title { get; set; } = "";
    [JsonPropertyName("description")]
    public string Description { get; set; } = "";
    [JsonPropertyName("default")]
    public object? Default { get; set; }
    [JsonPropertyName("minimum")]
    public decimal? Minimum { get; set; }
    [JsonPropertyName("maximum")]
    public decimal? Maximum { get; set; }
    // Yukki：枚举标签与真实配置值分别传递。
    [JsonPropertyName("enum")]
    public List<JsonElement>? Enum { get; set; }
    // 后端已按界面语言返回单语标签。
    [JsonPropertyName("x-enum-labels")]
    public List<string>? EnumLabels { get; set; }
    [JsonPropertyName("x-allow-custom")]
    public bool AllowCustom { get; set; }
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

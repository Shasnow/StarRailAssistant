using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class ExtensionsController(IBackendService backendService) : Controller
{
    // --- 列表 ---

    [HttpGet]
    [EndpointSummary("列出所有已注册的扩展")]
    [ProducesResponseType(200, Type = typeof(R<ExtensionInfo[]>))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> ListExtensions()
    {
        var extensions = await backendService.GetExtensionsAsync();
        return Ok(new R(true, "OK", extensions));
    }

    // --- Schema / Config ---

    [HttpGet("{id}/schema")]
    [EndpointSummary("获取扩展配置 Schema")]
    [ProducesResponseType(200, Type = typeof(R<ExtensionSchema>))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> GetSchema(string id)
    {
        var schema = await backendService.GetExtensionSchemaAsync(id);
        return Ok(schema is null
            ? new R(false, $"Extension '{id}' not found or has no config")
            : new R(true, "OK", schema));
    }

    [HttpGet("{id}/config")]
    [EndpointSummary("获取扩展配置值")]
    [ProducesResponseType(200, Type = typeof(R<string>))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> GetConfig(string id)
    {
        var json = await backendService.GetExtensionConfigAsync(id);
        return Ok(string.IsNullOrWhiteSpace(json)
            ? new R(false, $"Extension '{id}' has no config")
            : new R(true, "OK", json));
    }

    [HttpPut("{id}/config")]
    [EndpointSummary("设置扩展配置值")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> SetConfig(string id, [FromBody] string json)
    {
        var sent = await backendService.SendInputAsync($"extension config set {id} {json}");
        return Ok(new R(sent, sent ? "Config updated" : "Failed to update config."));
    }

    // --- 运行 / 停止 ---

    [HttpPost("{id}/run")]
    [EndpointSummary("运行指定扩展")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> RunExtension(string id, [FromQuery] string? config = null)
    {
        var cmd = string.IsNullOrEmpty(config)
            ? $"extension run {id}"
            : $"extension run {id} --config {config}";
        var sent = await backendService.SendInputAsync(cmd);
        return Ok(new R(sent, sent ? $"Extension '{id}' started" : $"Failed to start extension '{id}'"));
    }

    [HttpPost("{id}/stop")]
    [EndpointSummary("停止指定扩展")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> StopExtension(string id)
    {
        var sent = await backendService.SendInputAsync($"extension stop {id}");
        return Ok(new R(sent, sent ? $"Extension '{id}' stopped" : $"Failed to stop extension '{id}'"));
    }

    // --- 重载 ---

    [HttpPost("reload")]
    [EndpointSummary("重新扫描并导入扩展模块")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> ReloadExtensions()
    {
        var sent = await backendService.SendInputAsync("extension reload");
        return Ok(new R(sent, sent ? "Extensions reloaded" : "Failed to reload extensions"));
    }

}
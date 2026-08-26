using System.Runtime.Versioning;
using System.Security.Principal;
using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class ExtensionsController(IBackendService backendService) : Controller
{
    private static readonly TimeSpan BackendStartTimeout = TimeSpan.FromSeconds(3);

    // --- 列表 ---

    [HttpGet]
    [EndpointSummary("列出所有已注册的扩展")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> ListExtensions()
    {
        if (!await EnsureBackendReady())
            return StatusCode(500, new R(false, "Backend failed to start."));

        var extensions = await backendService.GetExtensionsAsync();
        return Ok(new R(true, "OK", extensions));
    }

    // --- Schema / Config ---

    [HttpGet("{id}/schema")]
    [EndpointSummary("获取扩展配置 Schema")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> GetSchema(string id)
    {
        if (!await EnsureBackendReady())
            return StatusCode(500, new R(false, "Backend failed to start."));

        var schema = await backendService.GetExtensionSchemaAsync(id);
        if (schema is null)
            return Ok(new R(false, $"Extension '{id}' not found or has no config"));
        return Ok(new R(true, "OK", schema));
    }

    [HttpGet("{id}/config")]
    [EndpointSummary("获取扩展配置值")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> GetConfig(string id)
    {
        if (!await EnsureBackendReady())
            return StatusCode(500, new R(false, "Backend failed to start."));

        var json = await backendService.GetExtensionConfigAsync(id);
        if (string.IsNullOrWhiteSpace(json))
            return Ok(new R(false, $"Extension '{id}' has no config"));
        return Ok(new R(true, "OK", json));
    }

    [HttpPut("{id}/config")]
    [EndpointSummary("设置扩展配置值")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> SetConfig(string id, [FromBody] string json)
    {
        if (!await EnsureBackendReady())
            return StatusCode(500, new R(false, "Backend failed to start."));

        var sent = await backendService.SendInputAsync($"extension config set {id} {json}");
        return Ok(new R(sent, sent ? "Config updated" : "Failed to send config command"));
    }

    // --- 运行 / 停止 ---

    [HttpPost("{id}/run")]
    [EndpointSummary("运行指定扩展")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> RunExtension(string id, [FromQuery] string? config = null)
    {
        if (!await EnsureBackendReady())
            return StatusCode(500, new R(false, "Backend failed to start."));

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
        if (!await EnsureBackendReady())
            return StatusCode(500, new R(false, "Backend failed to start."));

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
        if (!await EnsureBackendReady())
            return StatusCode(500, new R(false, "Backend failed to start."));

        var sent = await backendService.SendInputAsync("extension reload");
        return Ok(new R(sent, sent ? "Extensions reloaded" : "Failed to reload extensions"));
    }

    // --- Auto-Plot（保留原有端点） ---

    [HttpPost("auto-plot")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> SetAutoPlot([FromBody] AutoPlotRequest request)
    {
        if (OperatingSystem.IsWindows() && !IsAdministrator())
            return StatusCode(500, new R(false, "WebUI must be running as administrator before it can control SRA-cli extensions."));

        backendService.StartBackend("--inline");
        if (!await WaitForBackendReadyAsync())
            return StatusCode(500, new R(false, "Backend failed to start. Check WebUI logs for details."));

        var triggerSent = await backendService.SendInputAsync(
            request.Enabled ? "trigger enable AutoPlotTrigger" : "trigger disable AutoPlotTrigger");
        var skipSent = await backendService.SendInputAsync(
            $"trigger set AutoPlotTrigger skip_plot --type bool {request.SkipPlot.ToString().ToLowerInvariant()}");

        return Ok(new R(triggerSent && skipSent, triggerSent && skipSent ? "Auto plot updated" : "Failed to update auto plot"));
    }

    // --- 工具方法 ---

    private async Task<bool> EnsureBackendReady()
    {
        if (backendService.IsTaskRunning) return true;
        backendService.StartBackend("--inline --no-admin");
        return await WaitForBackendReadyAsync();
    }

    private async Task<bool> WaitForBackendReadyAsync()
    {
        var deadline = DateTimeOffset.UtcNow + BackendStartTimeout;
        while (DateTimeOffset.UtcNow < deadline)
        {
            if (await backendService.SendInputAsync("help"))
                return true;

            await Task.Delay(150);
        }

        return false;
    }

    [SupportedOSPlatform("windows")]
    private static bool IsAdministrator()
    {
        using var identity = WindowsIdentity.GetCurrent();
        var principal = new WindowsPrincipal(identity);
        return principal.IsInRole(WindowsBuiltInRole.Administrator);
    }
}

public record AutoPlotRequest(bool Enabled, bool SkipPlot);

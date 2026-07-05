using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Server.Services;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class TaskController(
    IBackendService backendService,
    LogStreamService logStream,
    IHostApplicationLifetime lifetime,
    ILogger<TaskController> logger) : Controller
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };
    private static readonly TimeSpan BackendStartTimeout = TimeSpan.FromSeconds(3);

    [HttpPost("run")]
    [EndpointSummary("运行任务")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(400)]
    [ProducesResponseType(409)]
    [ProducesResponseType(500)]
    public async Task<IActionResult> RunTask([FromBody] RunRequest request)
    {
        if (backendService.IsTaskRunning)
            return Conflict(new R(false, "A task is already running"));

        backendService.StartBackend("--inline --no-admin");
        if (!await WaitForBackendReadyAsync())
            return StatusCode(500, new R(false, "Backend failed to start. Check WebUI logs for details."));
        
        string? configName = null;

        if (request.Config is not null)
        {
            // WebUI can either persist an edited config or create a throwaway
            // config for one run.  The CLI still receives a config name, keeping
            // the backend command contract unchanged.
            configName = request.Persist
                ? request.Config.Name
                : $"_api_{Guid.NewGuid():N}";

            Directory.CreateDirectory(DataPath.ConfigsDir);
            var configPath = Path.Combine(DataPath.ConfigsDir, $"{configName}.json");
            var json = JsonSerializer.Serialize(request.Config, JsonOptions);
            await System.IO.File.WriteAllTextAsync(configPath, json);

            logger.LogInformation("{Action} config: {ConfigName}",
                request.Persist ? "Persisted" : "Created temporary", configName);
        }
        else if (!string.IsNullOrWhiteSpace(request.ConfigName))
        {
            configName = request.ConfigName;
            var configPath = Path.Combine(DataPath.ConfigsDir, $"{configName}.json");
            if (!System.IO.File.Exists(configPath))
                return BadRequest(new R(false, $"Config '{configName}' not found"));
        }

        var sent = await backendService.TaskRunAsync(configName);
        if (!sent)
            return StatusCode(500, new R(false, "Failed to send task command to backend."));

        return Ok(new R(true, "Task started"));
    }

    [HttpPost("stop")]
    [EndpointSummary("停止任务")]
    [ProducesResponseType(200, Type = typeof(R))]
    public async Task<IActionResult> StopTask()
    {
        if (!backendService.IsTaskRunning)
            return Ok(new R(false, "No task is running"));

        var sent = await backendService.TaskStopAsync();
        return Ok(sent ? new R(true, "Stop signal sent") : new R(false, "Failed to send stop signal"));
    }

    [HttpGet("status")]
    [EndpointSummary("获取任务状态")]
    [ProducesResponseType(200, Type = typeof(JsonDocument))]
    public async Task<IActionResult> GetTaskStatus()
    {
        var json = await backendService.GetTaskStatusAsync();
        try
        {
            return Ok(JsonDocument.Parse(json));
        }
        catch (JsonException)
        {
            return StatusCode(500, new R(false, "Failed to parse task status JSON"));
        }
    }

    [HttpGet("logs")]
    [EndpointSummary("获取最近日志")]
    [ProducesResponseType(200, Type = typeof(List<string>))]
    public IActionResult GetRecentLogs([FromQuery] int count = 100)
    {
        return Ok(logStream.GetRecentLogs(count));
    }

    [HttpGet("logs/stream")]
    [EndpointSummary("SSE 日志流")]
    [Produces("text/event-stream")]
    public async Task StreamLogs(CancellationToken cancellationToken)
    {
        Response.Headers.ContentType = "text/event-stream";
        Response.Headers.CacheControl = "no-cache";
        Response.Headers.Connection = "keep-alive";

        using var linkedCts = CancellationTokenSource.CreateLinkedTokenSource(
            cancellationToken, lifetime.ApplicationStopping);

        try
        {
            await foreach (var line in logStream.Subscribe(linkedCts.Token))
            {
                await Response.WriteAsync($"data: {line}\n\n", linkedCts.Token);
                await Response.Body.FlushAsync(linkedCts.Token);
            }
        }
        catch (OperationCanceledException)
        {
            // Client disconnected or the host is shutting down.
        }
    }

    private async Task<bool> WaitForBackendReadyAsync()
    {
        var deadline = DateTimeOffset.UtcNow + BackendStartTimeout;
        while (DateTimeOffset.UtcNow < deadline)
        {
            // There is no dedicated readiness endpoint for the CLI process, so a
            // harmless built-in command is used as the readiness probe.
            if (await backendService.SendInputAsync("help"))
                return true;

            await Task.Delay(150);
        }

        return false;
    }
}

public class RunRequest
{
    public string? ConfigName { get; set; }
    public TasksConfig? Config { get; set; }
    public bool Persist { get; set; }
}

public record R(bool Success, string Message, object? Data = null);

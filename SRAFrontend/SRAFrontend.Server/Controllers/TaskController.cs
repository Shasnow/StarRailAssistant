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

    [HttpPost("run")]
    [EndpointSummary("运行任务")]
    [EndpointDescription("运行任务。支持两种方式: 1) 通过 ConfigName 指定本地已保存的配置; 2) 通过 Config 对象直接传入完整配置。若使用 Config 对象，可通过 Persist 参数控制是否持久化到磁盘。")]
    [ProducesResponseType(200, Description = "任务运行成功")]
    [ProducesResponseType(400, Description = "请求参数无效")]
    [ProducesResponseType(409, Description = "任务已在运行")]
    [ProducesResponseType(500, Description = "发送运行命令失败")]
    public async Task<IActionResult> RunTask([FromBody] RunRequest request)
    {
        backendService.StartBackend("--no-admin --inline"); // 确保后端已启动，才能处理后续逻辑

        if (backendService.IsTaskRunning)
            return Conflict(new R(false, "A task is already running"));

        string? configName = null;

        if (request.Config is not null)
        {
            // 使用请求体中的完整配置
            configName = string.IsNullOrWhiteSpace(request.Config.Name)
                ? $"_api_{Guid.NewGuid():N}"
                : request.Config.Name;

            if (!request.Persist)
            {
                // 不持久化 → 使用临时名称
                configName = $"_api_{Guid.NewGuid():N}";
            }

            // 写入磁盘供 CLI 加载
            Directory.CreateDirectory(DataPath.ConfigsDir);
            var configPath = Path.Combine(DataPath.ConfigsDir, $"{configName}.json");
            var json = JsonSerializer.Serialize(request.Config, JsonOptions);
            await System.IO.File.WriteAllTextAsync(configPath, json);

            logger.LogInformation("{Action} config: {ConfigName}",
                request.Persist ? "Persisted" : "Created temporary", configName);
        }
        else if (!string.IsNullOrWhiteSpace(request.ConfigName))
        {
            // 使用本地已保存的配置
            configName = request.ConfigName;
            var configPath = Path.Combine(DataPath.ConfigsDir, $"{configName}.json");
            if (!System.IO.File.Exists(configPath))
                return BadRequest(new R(false, $"Config '{configName}' not found"));
        }

        var ok = backendService.TaskRun(configName);
        return ok
            ? Ok(new R(true, "Task started"))
            : StatusCode(500, new R(false, "Failed to send run command"));
    }

    [HttpPost("stop")]
    [EndpointSummary("停止任务")]
    [EndpointDescription("停止当前运行的任务")]
    [ProducesResponseType(200, Type = typeof(R))]
    public IActionResult StopTask()
    {
        if (!backendService.IsTaskRunning)
            return Ok(new R(false, "No task is running"));

        backendService.TaskStop();
        return Ok(new R(true, "Stop signal sent"));
    }

    [HttpGet("status")]
    [EndpointSummary("获取任务状态")]
    [EndpointDescription("获取当前任务是否正在运行")]
    [ProducesResponseType(200, Type = typeof(bool))]
    public IActionResult GetStatus()
    {
        return Ok(backendService.IsTaskRunning);
    }

    [HttpGet("logs")]
    [EndpointSummary("获取最近日志")]
    [EndpointDescription("获取最近的任务日志条目（默认100条）")]
    [ProducesResponseType(200, Type = typeof(List<string>))]
    public IActionResult GetRecentLogs([FromQuery] int count = 100)
    {
        return Ok(logStream.GetRecentLogs(count));
    }

    [HttpGet("logs/stream")]
    [EndpointSummary("SSE 日志流")]
    [EndpointDescription("通过 Server-Sent Events 实时推送任务日志")]
    [Produces("text/event-stream")]
    public async Task StreamLogs(CancellationToken cancellationToken)
    {
        Response.Headers.ContentType = "text/event-stream";
        Response.Headers.CacheControl = "no-cache";
        Response.Headers.Connection = "keep-alive";

        // 合并请求取消令牌和应用停止令牌
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
            // 客户端断开连接或服务器关闭，正常退出
        }
    }
}

public class RunRequest
{
    /// <summary>本地已保存的配置名称</summary>
    public string? ConfigName { get; set; }

    /// <summary>请求体中携带的完整配置</summary>
    public TasksConfig? Config { get; set; }

    /// <summary>是否持久化内联配置到磁盘（仅当 Config 不为 null 时有效）</summary>
    public bool Persist { get; set; }
}

public record R(bool Success, string Message);
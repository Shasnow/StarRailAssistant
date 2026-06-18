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
    [EndpointDescription(
        "运行任务。支持三种方式: 1) 不传 ConfigName 和 Config → 运行全部配置; 2) 通过 Config 传入完整配置，根据 Persist 决定是否持久化; 3) 通过 ConfigName 加载本地已保存的配置。")]
    [ProducesResponseType(200, Description = "已请求任务运行")]
    [ProducesResponseType(400, Description = "请求参数无效")]
    [ProducesResponseType(409, Description = "任务已在运行")]
    public async Task<IActionResult> RunTask([FromBody] RunRequest request)
    {
        backendService.StartBackend("--no-admin --inline"); // 确保后端已启动

        if (backendService.IsTaskRunning)
            return Conflict(new R(false, "A task is already running"));

        string? configName = null;

        if (request.Config is not null)
        {
            // 情况 2：携带完整配置 → 运行该配置
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
            // 情况 3：指定配置名 → 加载本地配置
            configName = request.ConfigName;
            var configPath = Path.Combine(DataPath.ConfigsDir, $"{configName}.json");
            if (!System.IO.File.Exists(configPath))
                return BadRequest(new R(false, $"Config '{configName}' not found"));
        }
        // 情况 1：两者都为空 → configName 为 null，运行全部配置

        await backendService.TaskRunAsync(configName);
        return Ok(new R(true, "Task started"));
    }

    [HttpPost("stop")]
    [EndpointSummary("停止任务")]
    [EndpointDescription("停止当前运行的任务")]
    [ProducesResponseType(200, Type = typeof(R))]
    public async Task<IActionResult> StopTask()
    {
        if (!backendService.IsTaskRunning)
            return Ok(new R(false, "No task is running"));

        await backendService.TaskStopAsync();
        return Ok(new R(true, "Stop signal sent"));
    }

    [HttpGet("status")]
    [EndpointSummary("获取任务状态")]
    [EndpointDescription("获取当前任务是否正在运行")]
    [ProducesResponseType(200, Type = typeof(bool), Description = "如果任务正在运行返回 true，否则返回 false")]
    public IActionResult GetStatus()
    {
        return Ok(backendService.IsTaskRunning);
    }

    [HttpGet("logs")]
    [EndpointSummary("获取最近日志")]
    [EndpointDescription("获取最近的任务日志条目（默认100条）")]
    [ProducesResponseType(200, Type = typeof(List<string>), Description = "一个字符串列表，每个元素为一条完整日志")]
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
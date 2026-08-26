using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class TaskController(
    IBackendService backendService,
    ILogger<TaskController> logger) : Controller
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

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
        return Ok(sent
            ? new R(true, "Task started")
            : new R(false, "Failed to send task command to backend."));
    }

    [HttpPost("single")]
    [EndpointSummary("运行单个指定任务")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(409)]
    [ProducesResponseType(500)]
    public async Task<IActionResult> RunSingleTask([FromBody] SingleTaskRequest request)
    {
        if (backendService.IsTaskRunning)
            return Conflict(new R(false, "A task is already running"));

        var sent = await backendService.TaskSingleAsync(request.TaskName, request.ConfigName);
        return Ok(sent 
            ? new R(true, "Single task started")
            : new R(false, "Failed to send single task command"));
    }

    [HttpPost("stop")]
    [EndpointSummary("停止任务")]
    [ProducesResponseType(200, Type = typeof(R))]
    public async Task<IActionResult> StopTask()
    {
        if (!backendService.IsTaskRunning)
            return Ok(new R(false, "No task is running"));

        var sent = await backendService.TaskStopAsync();
        return Ok(sent
            ? new R(true, "Stop signal sent")
            : new R(false, "Failed to send stop signal"));
    }

    [HttpGet("status")]
    [EndpointSummary("获取任务状态")]
    [ProducesResponseType(200, Type = typeof(R))]
    public async Task<IActionResult> GetTaskStatus()
    {
        var response = await backendService.GetTaskStatusAsync();
        return Ok(response);
    }

}

public class RunRequest
{
    public string? ConfigName { get; set; }
    public TasksConfig? Config { get; set; }
    public bool Persist { get; set; }
}

public class SingleTaskRequest
{
    public string TaskName { get; set; } = "";
    public string? ConfigName { get; set; }
}

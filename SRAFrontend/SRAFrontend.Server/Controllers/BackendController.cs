using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Server.Services;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class BackendController(
    IBackendService backendService,
    LogStreamService logStream,
    IHostApplicationLifetime lifetime): Controller
{
    [HttpPost("restart")]
    [EndpointSummary("重启后端")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> RestartBackend([FromBody] RestartRequest? request)
    {
        try
        {
            await backendService.RestartBackendAsync(request?.Arguments ?? "--inline --no-admin");
            return Ok(new R(true, "Backend restarted successfully"));
        }
        catch (Exception)
        {
            return StatusCode(500, new R(false, "Failed to restart backend"));
        }
    }
    
    [HttpPost("stop")]
    [EndpointSummary("停止后端")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public IActionResult StopBackend()
    {
        try
        {
            backendService.StopBackend();
            return Ok(new R(true, "Backend stopped successfully"));
        }
        catch (Exception)
        {
            return StatusCode(500, new R(false, "Failed to stop backend"));
        }
    }

    [HttpGet("logs")]
    [EndpointSummary("获取最近日志")]
    [ProducesResponseType(200, Type = typeof(List<string>))]
    public IActionResult GetRecentLogs([FromQuery] int count = 100)
    {
        return Ok(new R(true, "success", logStream.GetRecentLogs(count)));
    }

    [HttpGet("logs/stream")]
    [EndpointSummary("SSE 日志流")]
    [Produces("text/event-stream")]
    public async Task StreamLogs(CancellationToken cancellationToken)
    {
        Response.Headers.ContentType = "text/event-stream";
        Response.Headers.CacheControl = "no-cache";
        Response.Headers.Connection = "keep-alive";
        await Response.WriteAsync("* Connected *\n\n", cancellationToken);
        await Response.Body.FlushAsync(cancellationToken); // 没有这行，响应头会一直被缓冲

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
    
    [HttpGet("screenshot")]
    [EndpointSummary("获取 Operator 截图")]
    [ProducesResponseType(200, Type = typeof(FileContentResult))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> GetScreenshot()
    {
        var (msg, bytes) = await backendService.GetGameScreenshotBytesAsync();
        if (bytes.Length == 0)
        {
            return Ok(new R(false, $"Failed to get screenshot from backend: {msg}"));
        }
        return File(bytes, "image/jpeg");
    }
}

public record RestartRequest(string Arguments);
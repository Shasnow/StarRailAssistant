using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class OperatorController(IBackendService backendService) : Controller
{
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
        return File(bytes, "image/png");
    }
    
    
    [HttpGet("list")]
    [EndpointSummary("列出所有可用的 Operator 方法")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> ListMethods()
    {
        var response = await backendService.SendInputAndWaitObjectAsync("operator list --json");
        if (response is null)
            return StatusCode(500, new R(false, "No response from backend"));
        return Ok(response);
    }

    [HttpGet("help/{method}")]
    [EndpointSummary("获取 Operator 方法的详细帮助")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> GetMethodHelp(string method)
    {
        var response = await backendService.SendInputAndWaitObjectAsync($"operator help {method} --json");
        if (response is null)
            return StatusCode(500, new R(false, "No response from backend"));
        return Ok(response);
    }

    [HttpPost("call")]
    [EndpointSummary("调用 Operator 方法")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(400)]
    [ProducesResponseType(500)]
    public async Task<IActionResult> CallMethod([FromBody] OperatorCallRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Method))
            return BadRequest(new R(false, "method is required"));

        var parameters = request.Params == null ? "" : request.Params.ToString();
        var response = await backendService.SendInputAndWaitObjectAsync($"operator call {request.Method} '{parameters}' --json");
        if (response is null)
            return StatusCode(500, new R(false, "No response from backend"));
        return Ok(response);
    }

    // --- 工具方法 ---
}

public record OperatorCallRequest(string Method, JsonElement? Params);

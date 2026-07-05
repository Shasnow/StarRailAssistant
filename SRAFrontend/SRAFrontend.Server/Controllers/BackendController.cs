using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class BackendController(IBackendService backendService): Controller
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
}

public record RestartRequest(string Arguments);
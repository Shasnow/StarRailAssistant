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

    [HttpPost("warp-forecast/run")]
    [ProducesResponseType(200, Type = typeof(R))]
    [ProducesResponseType(500)]
    public async Task<IActionResult> RunWarpForecast()
    {
        if (OperatingSystem.IsWindows() && !IsAdministrator())
            return StatusCode(500, new R(false, "WebUI must be running as administrator before it can start SRA-cli tasks."));

        var sent = await backendService.TaskSingleAsync("WarpForecastTask");
        return Ok(sent ? new R(true, "Warp forecast task started") : new R(false, "Failed to start warp forecast task"));
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

using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class AppController(AppService appService): Controller
{
    [HttpGet("background")]
    [EndpointSummary("获取背景图")]
    [ProducesResponseType(200, Type = typeof(byte[]))]
    public async Task<IActionResult> GetBackgroundImage()
    {
        var imageBytes = await appService.GetBackgroundImageAsync();
        return File(imageBytes, "image/jpeg");
    }
    
    [HttpGet("system-info")]
    [EndpointSummary("获取系统信息")]
    [ProducesResponseType(200, Type = typeof(R))]
    public IActionResult GetSystemInfo()
    {
        var systemInfo = appService.GetSystemInfo();
        return Ok(new R(true, "success", systemInfo));
    }
}
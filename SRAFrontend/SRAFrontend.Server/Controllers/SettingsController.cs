using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class SettingsController(SettingsService settingsService) : Controller
{
    [HttpGet]
    [EndpointSummary("获取设置")]
    [EndpointDescription("获取当前应用程序的设置")]
    [ProducesResponseType(200, Type = typeof(AppSettings))]
    public IActionResult GetSettings()
    {
        return Ok(settingsService.Settings);
    }
    
}
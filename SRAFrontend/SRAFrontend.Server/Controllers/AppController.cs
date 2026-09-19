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
}
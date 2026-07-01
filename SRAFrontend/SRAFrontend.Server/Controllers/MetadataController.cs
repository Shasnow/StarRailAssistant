using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Models;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class MetadataController : Controller
{
    [HttpGet("trailblaze-power/tasks")]
    [ProducesResponseType(200)]
    public IActionResult GetTrailblazePowerTasks()
    {
        return Ok(TpTaskItems.TaskItems.Select((item, index) => new
        {
            index,
            item.Id,
            item.Name,
            item.Cost,
            item.MaxSingleTimes,
            Levels = item.Levels.Select((name, levelIndex) => new
            {
                index = levelIndex,
                name
            })
        }));
    }
}

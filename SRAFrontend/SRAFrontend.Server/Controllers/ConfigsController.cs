using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class ConfigsController(ConfigService configService, CacheService cacheService) : Controller
{
    [HttpGet]
    [EndpointSummary("获取所有配置名称")]
    [ProducesResponseType(200, Type = typeof(List<string>))]
    public IActionResult GetConfigNames()
    {
        return Ok(cacheService.Cache.ConfigNames);
    }

    [HttpGet("{configName}")]
    [EndpointSummary("获取指定配置")]
    [ProducesResponseType(200, Type = typeof(TasksConfig))]
    [ProducesResponseType(404)]
    public IActionResult GetConfig(string configName)
    {
        if (!cacheService.Cache.ConfigNames.Contains(configName))
            return NotFound();

        configService.Load(configName);
        return Ok(configService.TasksConfig);
    }

    [HttpPost("{configName}")]
    [EndpointSummary("新建配置")]
    [ProducesResponseType(200)]
    [ProducesResponseType(400, Description = "名称包含非法字符")]
    [ProducesResponseType(409, Description = "配置已存在")]
    public IActionResult CreateConfig(string configName)
    {
        if (configName.IndexOfAny(['\\', '/', ':', '*', '?', '"', '<', '>', '|']) != -1)
            return BadRequest("Config name contains invalid characters");

        if (cacheService.Cache.ConfigNames.Contains(configName))
            return Conflict("Config name already exists");

        cacheService.Cache.ConfigNames.Add(configName);
        return Ok(configName);
    }

    [HttpPut("{configName}")]
    [EndpointSummary("更新配置")]
    [ProducesResponseType(200)]
    [ProducesResponseType(404)]
    public IActionResult UpdateConfig(string configName, [FromBody] TasksConfig config)
    {
        if (!cacheService.Cache.ConfigNames.Contains(configName))
            return NotFound();

        config.Name = configName;
        configService.TasksConfig = config;
        configService.Save();
        return Ok();
    }

    [HttpDelete("{configName}")]
    [EndpointSummary("删除配置")]
    [ProducesResponseType(200)]
    [ProducesResponseType(404)]
    public IActionResult DeleteConfig(string configName)
    {
        if (!cacheService.Cache.ConfigNames.Remove(configName))
            return NotFound();

        return Ok(configName);
    }
}

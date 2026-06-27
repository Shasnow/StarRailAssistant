using System.Text.Json;
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
        return Ok(CreateSafeConfigPayload(configService.TasksConfig));
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
        cacheService.SaveCache();
        return Ok(configName);
    }

    [HttpPut("{configName}")]
    [EndpointSummary("更新配置")]
    [ProducesResponseType(200)]
    [ProducesResponseType(404)]
    public IActionResult UpdateConfig(string configName, [FromBody] JsonElement body)
    {
        if (!cacheService.Cache.ConfigNames.Contains(configName))
            return NotFound();

        configService.Load(configName);
        var currentStartGame = configService.TasksConfig?.StartGame;
        var config = body.Deserialize<TasksConfig>();
        if (config is null)
            return BadRequest("Invalid config payload");

        config.Name = configName;
        if (body.TryGetProperty("startGame", out var startGame))
        {
            if (startGame.TryGetProperty("username", out var username))
                config.StartGame.Username = username.GetString() ?? "";
            else
                config.StartGame.Username = currentStartGame?.Username ?? "";

            if (startGame.TryGetProperty("password", out var password))
                config.StartGame.Password = password.GetString() ?? "";
            else
                config.StartGame.Password = currentStartGame?.Password ?? "";
        }
        else
        {
            config.StartGame.Username = currentStartGame?.Username ?? "";
            config.StartGame.Password = currentStartGame?.Password ?? "";
        }

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

        cacheService.SaveCache();
        return Ok(configName);
    }

    private static object? CreateSafeConfigPayload(TasksConfig? config)
    {
        if (config is null)
            return null;

        var node = JsonSerializer.SerializeToNode(config);
        if (node?["startGame"] is System.Text.Json.Nodes.JsonObject startGame)
        {
            startGame.Remove("username");
            startGame.Remove("password");
            startGame.Remove("encryptedUsername");
            startGame.Remove("encryptedPassword");
        }

        return node;
    }
}

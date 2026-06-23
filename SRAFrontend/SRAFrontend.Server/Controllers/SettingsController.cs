using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class SettingsController(SettingsService settingsService, ILogger<SettingsController> logger) : Controller
{
    [HttpGet]
    [EndpointSummary("获取设置")]
    [EndpointDescription("获取当前应用程序的设置")]
    [ProducesResponseType(200, Type = typeof(AppSettings))]
    public IActionResult GetSettings()
    {
        return Ok(settingsService.Settings);
    }

    [HttpPut]
    [EndpointSummary("修改设置")]
    [EndpointDescription("按字段修改设置，支持只传需要修改的部分。请求体为 AppSettings 的部分 JSON，例如 { \"advanced\": { \"backend.remote.enabled\": true } }")]
    [ProducesResponseType(200)]
    [ProducesResponseType(400)]
    public IActionResult UpdateSettings([FromBody] JsonElement body)
    {
        var settings = settingsService.Settings;
        var updated = new List<string>();

        foreach (var sectionProp in body.EnumerateObject())
        {
            // 找到 AppSettings 中匹配的 section（如 "advanced" -> Settings.Advanced）
            var section = GetSection(settings, sectionProp.Name);
            if (section is null)
            {
                logger.LogWarning("Unknown settings section: {Section}", sectionProp.Name);
                continue;
            }

            foreach (var fieldProp in sectionProp.Value.EnumerateObject())
            {
                if (SetFieldByJsonName(section, fieldProp.Name, fieldProp.Value))
                {
                    updated.Add($"{sectionProp.Name}.{fieldProp.Name}");
                }
                else
                {
                    logger.LogWarning("Unknown field: {Section}.{Field}", sectionProp.Name, fieldProp.Name);
                }
            }
        }

        if (updated.Count == 0)
            return BadRequest(new { message = "No valid settings were updated" });

        logger.LogInformation("Updated settings: {Fields}", string.Join(", ", updated));
        return Ok(new { updated });
    }

    private static object? GetSection(AppSettings settings, string name)
    {
        return name switch
        {
            "general" => settings.General,
            "display" => settings.Display,
            "update" => settings.Update,
            "advanced" => settings.Advanced,
            "notification" => settings.Notification,
            "warpForecast" => settings.WarpForecast,
            _ => null
        };
    }

    private static bool SetFieldByJsonName(object section, string jsonName, JsonElement value)
    {
        var type = section.GetType();

        foreach (var prop in type.GetProperties())
        {
            var attr = prop.GetCustomAttributes(typeof(JsonPropertyNameAttribute), false)
                .OfType<JsonPropertyNameAttribute>()
                .FirstOrDefault();

            if (attr?.Name != jsonName) continue;
            if (!prop.CanWrite) continue;

            var converted = value.Deserialize(prop.PropertyType);
            prop.SetValue(section, converted);
            return true;
        }

        return false;
    }
}

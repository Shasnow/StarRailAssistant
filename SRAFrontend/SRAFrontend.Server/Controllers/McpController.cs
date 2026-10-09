using System.ComponentModel;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using ModelContextProtocol.Protocol;
using ModelContextProtocol.Server;
using SRAFrontend.Models;
using SRAFrontend.Server.Services;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[McpServerToolType]
public class McpController(
    IBackendService backendService,
    LogStreamService logStreamService,
    SettingsService settingsService,
    ConfigService configService,
    CacheService cacheService)
{
    private const string NoResponseMsg = "(No response from backend, is the backend running?)";
    
    [McpServerTool(Name = "sra_screenshot")]
    [Description("Take a screenshot(720p) of the game window(1080p)")]
    public async Task<IEnumerable<ContentBlock>> TakeScreenshotAsync()
    {
        var (msg, screenshotBytes) = await backendService.GetGameScreenshotBytesAsync();
        if (screenshotBytes.Length == 0)
            return [new TextContentBlock { Text = msg }];
        return
        [
            ImageContentBlock.FromBytes(screenshotBytes, "image/jpeg"),
            new TextContentBlock
                { Text = "You must convert coordinates from 720p to 1080p if you want to use them in other tools." }
        ];
    }

    [McpServerTool(Name = "sra_startup")]
    [Description("Start StarRailAssistant Backend")]
    public string StartBackend()
    {
        // --no-admin：禁止后端 UAC 自重启，保持进程为 server 子进程（与 BackendController 一致）
        return backendService.StartBackend("--inline --no-admin")
            ? "StarRailAssistant Backend started successfully."
            : "Failed to start StarRailAssistant Backend (executable not found or launch error).";
    }

    [McpServerTool(Name = "sra_shutdown")]
    [Description("Shutdown StarRailAssistant Backend")]
    public string ShutdownBackend()
    {
        return backendService.StopBackend()
            ? "StarRailAssistant Backend shutdown successfully."
            : "StarRailAssistant Backend is not running.";
    }

    [McpServerTool(Name = "sra_restart")]
    [Description("Restart StarRailAssistant Backend")]
    public async Task<string> RestartBackend()
    {
        return await backendService.RestartBackendAsync("--inline --no-admin")
            ? "StarRailAssistant Backend restarted successfully."
            : "Failed to restart StarRailAssistant Backend (executable not found or launch error).";
    }

    [McpServerTool(Name = "sra_task_list")]
    [Description("List all available tasks")]
    public async Task<string> ListTasksAsync()
    {
        return await backendService.TaskListAsync() ?? NoResponseMsg;
    }

    [McpServerTool(Name = "sra_task_run")]
    [Description("Run all selected tasks in given config(s)")]
    public async Task<string> RunTasksAsync(
        [Description("Config name(s) or absolute path(s) to run, space-separated, empty for all configs")]
        string? configNames = null)
    {
        var success = await backendService.TaskRunAsync(configNames);
        return success
            ? "Successfully started tasks. Check the task status or logs for progress."
            : "Failed to start tasks.";
    }

    [McpServerTool(Name = "sra_task_single")]
    [Description("Run a single task by name or index")]
    public async Task<string> RunSingleTaskAsync(
        [Description("Task name or index to run")]
        string task,
        [Description("Config name or absolute path to use, empty for current config")]
        string? configName = null)
    {
        var success = await backendService.TaskSingleAsync(task, configName);
        return success
            ? $"Successfully started task '{task}'. Check the task status or logs for progress."
            : $"Failed to start task '{task}'.";
    }

    [McpServerTool(Name = "sra_task_stop")]
    [Description("Stop the currently running task")]
    public async Task<string> StopTaskAsync()
    {
        var success = await backendService.TaskStopAsync();
        return success
            ? "Successfully sent stop signal to the running task."
            : "Failed to send stop signal. No task may be running.";
    }

    [McpServerTool(Name = "sra_task_status")]
    [Description("Get the status of the currently running task")]
    public async Task<string> GetTaskStatusAsync()
    {
        var status = await backendService.GetTaskStatusAsync();
        return JsonSerializer.Serialize(status, JsonSerializerOptions.Web);
    }

    [McpServerTool(Name = "sra_ocr")]
    [Description("Perform OCR on the game window, returns all recognized texts")]
    public async Task<IEnumerable<string>> PerformOcrAsync(
        int? fromX = null,
        int? fromY = null,
        int? toX = null,
        int? toY = null)
    {
        var parameters = new { from_x = fromX, from_y = fromY, to_x = toX, to_y = toY };
        var response = await backendService.OperatorCallAsync("ocr", parameters);
        return [JsonSerializer.Serialize(response, JsonSerializerOptions.Web)
        , "Coordinates are in 1080p game window pixels."];
    }

    [McpServerTool(Name = "sra_ocr_match")]
    [Description("Perform OCR and match text on the game window, returns the matched text")]
    public async Task<IEnumerable<string>> PerformOcrMatchAsync(
        [Description("Target text to match")] string text,
        int? fromX = null, int? fromY = null, int? toX = null, int? toY = null)
    {
        var parameters = new { text, from_x = fromX, from_y = fromY, to_x = toX, to_y = toY };
        var response = await backendService.OperatorCallAsync("ocr_match", parameters);
        return [JsonSerializer.Serialize(response, JsonSerializerOptions.Web),
        "Coordinates are in 1080p game window pixels."];
    }

    [McpServerTool(Name = "sra_click_point")]
    [Description("Click on a point in the game window")]
    public async Task<string> ClickPointAsync(
        [Description("Click mode: 'abs' for absolute pixels in the 1080p game window, 'rel' for relative coordinates (0.0-1.0)")]
        string mode,
        [Description("X coordinate to click")] double x,
        [Description("Y coordinate to click")] double y)
    {
        if (mode is not ("abs" or "rel"))
            return $"Invalid mode '{mode}', expected \"abs\" or \"rel\".";
        var parameters = new { mode, x, y };
        return (await backendService.OperatorCallAsync("click_point", parameters))?.Message ??
               NoResponseMsg;
    }

    [McpServerTool(Name = "sra_operator_list")]
    [Description("List all available operator methods")]
    public async Task<string> ListOperatorMethodsAsync()
    {
        var response = await backendService.SendInputAndWaitObjectAsync("operator list --json");
        return response is null ? NoResponseMsg : JsonSerializer.Serialize(response, JsonSerializerOptions.Web);
    }

    [McpServerTool(Name = "sra_operator_help")]
    [Description("Get detailed help (parameters, types and doc) for an operator method")]
    public async Task<string> OperatorHelpAsync(
        [Description("Operator method name")] string method)
    {
        if (!IsValidMethodName(method))
            return $"Invalid method name '{method}'.";
        var response = await backendService.SendInputAndWaitObjectAsync($"operator help {method} --json");
        return response is null ? NoResponseMsg : JsonSerializer.Serialize(response, JsonSerializerOptions.Web);
    }

    [McpServerTool(Name = "sra_operator_call")]
    [Description("Call any operator method with JSON parameters. Use sra_operator_list to discover methods and sra_operator_help for their parameters.")]
    public async Task<string> OperatorCallAsync(
        [Description("Operator method name, e.g. 'click_point'")] string method,
        [Description("Method parameters as a JSON object string, e.g. '{\"mode\":\"rel\",\"x\":0.5,\"y\":0.5}'. Empty for no parameters.")]
        string? parameters = null)
    {
        if (!IsValidMethodName(method))
            return $"Invalid method name '{method}'.";

        object paramObject = new { };
        if (!string.IsNullOrWhiteSpace(parameters))
        {
            try
            {
                var element = JsonSerializer.Deserialize<JsonElement>(parameters);
                if (element.ValueKind != JsonValueKind.Object)
                    return "parameters must be a JSON object, e.g. '{\"x\":1}'";
                paramObject = element;
            }
            catch (JsonException e)
            {
                return $"Invalid parameters JSON: {e.Message}";
            }
        }

        var response = await backendService.OperatorCallAsync(method, paramObject);
        return response is null ? NoResponseMsg : JsonSerializer.Serialize(response, JsonSerializerOptions.Web);
    }

    private static bool IsValidMethodName(string method) =>
        !string.IsNullOrWhiteSpace(method) && method.All(c => char.IsAsciiLetterOrDigit(c) || c == '_');

    [McpServerTool(Name = "sra_scroll")]
    [Description("Scroll the mouse wheel")]
    public async Task<string> ScrollAsync(
        [Description("The number of clicks to scroll, positive for up, negative for down")] int clicks,
        [Description("X coordinate of the scroll position, null for current position")] int? x=null,
        [Description("Y coordinate of the scroll position, null for current position")] int? y=null)
    {
        var parameters = new { clicks, x, y };
        return (await backendService.OperatorCallAsync("scroll", parameters))?.Message ??
               NoResponseMsg;
    }

    [McpServerTool(Name = "sra_press_key")]
    [Description("Press a key on the keyboard")]
    public async Task<string> PressKeyAsync(
        [Description("The key to press, combinations like 'w+d' are supported")]
        string key)
    {
        var parameters = new { key };
        return (await backendService.OperatorCallAsync("press_key", parameters))?.Message ??
               NoResponseMsg;
    }
    
    [McpServerTool(Name = "sra_hold_key")]
    [Description("Hold a key on the keyboard")]
    public async Task<string> HoldKeyAsync(
        [Description("The key to hold, combinations like 'w+d' are supported")]
        string key,
        [Description("The duration to hold the key in seconds, default is 1.0s")]
        float duration = 1.0f)
    {
        var parameters = new { key, duration };
        return (await backendService.OperatorCallAsync("hold_key", parameters))?.Message ??
               NoResponseMsg;
    }

    [McpServerTool(Name = "sra_sleep")]
    [Description("Pause the execution for a specified number of seconds")]
    public async Task<string> SleepAsync(
        [Description("The number of seconds to sleep")]
        int seconds)
    {
        await Task.Delay(TimeSpan.FromSeconds(seconds));
        return $"Slept for {seconds} seconds";
    }
    
    [McpServerTool(Name = "sra_get_logs")]
    [Description("Get the backend logs")]
    public string GetLogsAsync(
        [Description("The number of log lines to retrieve, default is 100")]
        int count = 100)
    {
        return string.Join("\n", logStreamService.GetRecentLogs(count));
    }

    [McpServerTool(Name = "sra_config_list")]
    [Description("List all task config names and the current config name")]
    public string ListConfigs()
    {
        return JsonSerializer.Serialize(
            new { currentConfig = cacheService.Cache.CurrentConfigName, configs = cacheService.Cache.ConfigNames },
            JsonSerializerOptions.Web);
    }

    [McpServerTool(Name = "sra_config_get")]
    [Description("Get a task config by name (username/password are masked). Field keys are dotted keys like currencyWars.runtimes")]
    public string GetConfig(
        [Description("Config name")]
        string configName)
    {
        if (!cacheService.Cache.ConfigNames.Contains(configName))
            return $"Config '{configName}' not found.";
        configService.Load(configName);
        var config = configService.TasksConfig;
        if (config is null)
            return $"Failed to load config '{configName}'.";

        var node = JsonSerializer.SerializeToNode(config);
        if (node?["startGame"] is JsonObject startGame)
        {
            startGame["username"] = string.IsNullOrEmpty(config.StartGame.Username) ? "" : "******";
            startGame["password"] = string.IsNullOrEmpty(config.StartGame.Password) ? "" : "******";
        }

        return node?.ToJsonString(JsonSerializerOptions.Web) ?? "null";
    }

    [McpServerTool(Name = "sra_config_create")]
    [Description("Create a new task config (registers the name; the config file is written on first update)")]
    public string CreateConfig(
        [Description("Config name, must not contain \\/:*?\"<>|")]
        string configName)
    {
        if (configName.IndexOfAny(['\\', '/', ':', '*', '?', '"', '<', '>', '|']) != -1)
            return "Config name contains invalid characters";
        if (cacheService.Cache.ConfigNames.Contains(configName))
            return $"Config '{configName}' already exists";

        cacheService.Cache.ConfigNames.Add(configName);
        cacheService.SaveCache();
        return $"Config '{configName}' created.";
    }

    [McpServerTool(Name = "sra_config_update")]
    [Description("Patch a task config with a partial JSON object. Top-level keys are section names (startGame/trailblazePower/receiveRewards/cosmicStrife/missionAccomplished), inner keys are dotted field keys, e.g. {\"cosmicStrife\":{\"currencyWars.runtimes\":3,\"currencyWars.pointRewards\":true}}. Only provided fields are changed; startGame.username/password accept plaintext and are stored encrypted, unprovided fields are preserved.")]
    public string UpdateConfig(
        [Description("Config name")]
        string configName,
        [Description("Patch JSON string")]
        string patchJson)
    {
        if (!cacheService.Cache.ConfigNames.Contains(configName))
            return $"Config '{configName}' not found.";

        var jsonElement = ParsePatchObject(patchJson);
        if (jsonElement.ValueKind != JsonValueKind.Object)
            return "Patch JSON must be an object";

        configService.Load(configName);
        var config = configService.TasksConfig;
        if (config is null)
            return $"Failed to load config '{configName}'.";

        var updated = new List<string>();
        foreach (var sectionProp in jsonElement.EnumerateObject())
        {
            var section = GetConfigSection(config, sectionProp.Name);
            if (section is null)
                continue;
            foreach (var fieldProp in sectionProp.Value.EnumerateObject())
            {
                // username/password 的 json 名映射到加密存储属性，明文需走 Username/Password 属性由 Save() 加密
                if (sectionProp.Name == "startGame" && fieldProp.Name is "username" or "password")
                {
                    var text = fieldProp.Value.GetString() ?? "";
                    if (fieldProp.Name == "username")
                        config.StartGame.Username = text;
                    else
                        config.StartGame.Password = text;
                    updated.Add($"startGame.{fieldProp.Name}");
                    continue;
                }
                if (TrySetFieldByJsonName(section, fieldProp.Name, fieldProp.Value))
                    updated.Add($"{sectionProp.Name}.{fieldProp.Name}");
            }
        }

        if (updated.Count == 0)
            return "No valid fields were updated";

        configService.Save();
        return $"Config '{configName}' updated: {string.Join(", ", updated)}";
    }

    [McpServerTool(Name = "sra_config_delete")]
    [Description("Delete a task config registration (the config file on disk is kept)")]
    public string DeleteConfig(
        [Description("Config name")]
        string configName)
    {
        if (!cacheService.Cache.ConfigNames.Remove(configName))
            return $"Config '{configName}' not found.";
        cacheService.SaveCache();
        return $"Config '{configName}' deleted.";
    }

    [McpServerTool(Name = "sra_settings_get")]
    [Description("Get the app settings. Field keys are dotted keys like developerMode.customBackend.enabled")]
    public string GetSettings()
    {
        return JsonSerializer.Serialize(settingsService.Settings, JsonSerializerOptions.Web);
    }

    [McpServerTool(Name = "sra_settings_update")]
    [Description("Patch app settings with a partial JSON object. Top-level keys are section names (general/display/update/advanced/notification), inner keys are dotted field keys, e.g. {\"advanced\":{\"developerMode.customBackend.enabled\":true}}. Only provided fields are changed.")]
    public string UpdateSettings(
        [Description("Patch JSON string")]
        string patchJson)
    {
        var jsonElement = ParsePatchObject(patchJson);
        if (jsonElement.ValueKind != JsonValueKind.Object)
            return "Patch JSON must be an object";

        var settings = settingsService.Settings;
        var updated = new List<string>();
        foreach (var sectionProp in jsonElement.EnumerateObject())
        {
            var section = GetSettingsSection(settings, sectionProp.Name);
            if (section is null)
                continue;
            foreach (var fieldProp in sectionProp.Value.EnumerateObject())
            {
                if (TrySetFieldByJsonName(section, fieldProp.Name, fieldProp.Value))
                    updated.Add($"{sectionProp.Name}.{fieldProp.Name}");
            }
        }

        if (updated.Count == 0)
            return "No valid settings were updated";

        settingsService.Save();
        return $"Settings updated: {string.Join(", ", updated)}";
    }

    private static JsonElement ParsePatchObject(string patchJson)
    {
        try
        {
            var element = JsonSerializer.Deserialize<JsonElement>(patchJson);
            return element.ValueKind == JsonValueKind.Object ? element : default;
        }
        catch (JsonException)
        {
            return default;
        }
    }

    private static object? GetSettingsSection(AppSettings settings, string name) => name switch
    {
        "general" => settings.General,
        "display" => settings.Display,
        "update" => settings.Update,
        "advanced" => settings.Advanced,
        "notification" => settings.Notification,
        _ => null
    };

    private static object? GetConfigSection(TasksConfig config, string name) => name switch
    {
        "startGame" => config.StartGame,
        "trailblazePower" => config.TrailblazePower,
        "receiveRewards" => config.ReceiveRewards,
        "cosmicStrife" => config.CosmicStrife,
        "missionAccomplished" => config.MissionAccomplished,
        _ => null
    };

    private static bool TrySetFieldByJsonName(object section, string jsonName, JsonElement value)
    {
        foreach (var prop in section.GetType().GetProperties())
        {
            var attr = prop.GetCustomAttributes(typeof(JsonPropertyNameAttribute), false)
                .OfType<JsonPropertyNameAttribute>()
                .FirstOrDefault();
            if (attr?.Name != jsonName || !prop.CanWrite)
                continue;
            try
            {
                var converted = value.Deserialize(prop.PropertyType);
                prop.SetValue(section, converted);
                return true;
            }
            catch
            {
                return false;
            }
        }

        return false;
    }
}
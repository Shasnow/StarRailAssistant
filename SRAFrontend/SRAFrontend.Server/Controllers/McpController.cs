using System.ComponentModel;
using System.Text.Json;
using ModelContextProtocol.Protocol;
using ModelContextProtocol.Server;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[McpServerToolType]
public class McpController(IBackendService backendService)
{
    [McpServerTool(Name = "sra_screenshot")]
    [Description("Take a screenshot(720p) of the game window(1080p)")]
    public async Task<IEnumerable<ContentBlock>> TakeScreenshotAsync()
    {
        var (msg, screenshotBytes) = await backendService.GetGameScreenshotBytesAsync();
        if (screenshotBytes.Length == 0)
            return [new TextContentBlock { Text = msg }];
        return
        [
            ImageContentBlock.FromBytes(screenshotBytes, "image/png"),
            new TextContentBlock
                { Text = "You must convert coordinates from 720p to 1080p if you want to use them in other tools." }
        ];
    }

    [McpServerTool(Name = "sra_startup")]
    [Description("Start StarRailAssistant Backend")]
    public string StartBackend()
    {
        backendService.StartBackend("--inline");
        return "StarRailAssistant Backend started successfully.";
    }

    [McpServerTool(Name = "sra_shutdown")]
    [Description("Shutdown StarRailAssistant Backend")]
    public string ShutdownBackend()
    {
        backendService.StopBackend();
        return "StarRailAssistant Backend shutdown successfully.";
    }

    [McpServerTool(Name = "sra_task_list")]
    [Description("List all available tasks")]
    public async Task<string> ListTasksAsync()
    {
        return await backendService.TaskListAsync() ?? "(no response from backend)";
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
    public async Task<string> PerformOcrAsync(
        int? fromX = null,
        int? fromY = null,
        int? toX = null,
        int? toY = null)
    {
        var parameters = new { from_x = fromX, from_y = fromY, to_x = toX, to_y = toY };
        var response = await backendService.OperatorCallAsync("ocr", parameters);
        return JsonSerializer.Serialize(response, JsonSerializerOptions.Web);
    }

    [McpServerTool(Name = "sra_ocr_match")]
    [Description("Perform OCR and match text on the game window, returns the matched text")]
    public async Task<string> PerformOcrMatchAsync(
        [Description("Target text to match")] string text,
        int? fromX = null, int? fromY = null, int? toX = null, int? toY = null)
    {
        var parameters = new { text, from_x = fromX, from_y = fromY, to_x = toX, to_y = toY };
        var response = await backendService.OperatorCallAsync("ocr_match", parameters);
        return JsonSerializer.Serialize(response, JsonSerializerOptions.Web);
    }

    [McpServerTool(Name = "sra_click_point_abs")]
    [Description("Click on an absolute point in the game window")]
    public async Task<string> ClickPointAbsAsync(
        [Description("X coordinate to click")] int x,
        [Description("Y coordinate to click")] int y)
    {
        var parameters = new { x, y };
        return (await backendService.OperatorCallAsync("click_point", parameters))?.Message ??
               "(no response from backend)";
    }

    [McpServerTool(Name = "sra_click_point_rel")]
    [Description("Click on a relative point in the game window")]
    public async Task<string> ClickPointRelAsync(
        [Description("X coordinate to click, relative to the game window")]
        float x,
        [Description("Y coordinate to click, relative to the game window")]
        float y)
    {
        var parameters = new { x, y };
        return (await backendService.OperatorCallAsync("click_point", parameters))?.Message ??
               "(no response from backend)";
    }

    [McpServerTool(Name = "sra_scroll")]
    [Description("Scroll the mouse wheel")]
    public async Task<string> ScrollAsync(
        [Description("The number of clicks to scroll, positive for up, negative for down")] int clicks,
        [Description("X coordinate of the scroll position, null for current position")] int? x=null,
        [Description("Y coordinate of the scroll position, null for current position")] int? y=null)
    {
        var parameters = new { clicks, x, y };
        return (await backendService.OperatorCallAsync("scroll", parameters))?.Message ??
               "(no response from backend)";
    }

    [McpServerTool(Name = "sra_press_key")]
    [Description("Press a key on the keyboard")]
    public async Task<string> PressKeyAsync(
        [Description("The key to press, combinations like 'w+d' are supported")]
        string key)
    {
        var parameters = new { key };
        return (await backendService.OperatorCallAsync("press_key", parameters))?.Message ??
               "(no response from backend)";
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
               "(no response from backend)";
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
}
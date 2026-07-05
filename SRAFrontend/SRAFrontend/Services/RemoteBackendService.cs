using System;
using System.ComponentModel;
using System.IO;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

/// <summary>
/// 通过 HTTP 连接远程 Server 的 <see cref="IBackendService"/> 实现。
/// StartBackend 连接 SSE 日志流，TaskRun / TaskStop 调用对应 REST API。
/// </summary>
public class RemoteBackendService(IHttpClientFactory httpClientFactory, ILogger<RemoteBackendService> logger)
    : IBackendService
{
    private CancellationTokenSource? _sseCts;

    /// <summary>远程服务器基础地址，例如 http://192.168.1.100:5073</summary>
    public string BaseUrl { get; set; } = "http://localhost:5000";

    private HttpClient Client => httpClientFactory.CreateClient("GlobalClient");

    public event PropertyChangedEventHandler? PropertyChanged;
    public event Action<string>? Outputted;

    public bool IsTaskRunning
    {
        get;
        set
        {
            if (field == value) return;
            field = value;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(IsTaskRunning)));
        }
    }

    public void StartBackend(string arguments)
    {
        if (_sseCts is not null) return;

        _sseCts = new CancellationTokenSource();
        _ = ConnectAndRunAsync(_sseCts.Token);
        logger.LogInformation("Connecting to remote server at {BaseUrl}", BaseUrl);
    }

    public void StopBackend()
    {
        if (_sseCts is null) return;
        _sseCts.Cancel();
        _sseCts.Dispose();
        _sseCts = null;
        IsTaskRunning = false;
        logger.LogInformation("Disconnected from remote server");
    }

    public async Task RestartBackendAsync(string arguments)
    {
        StopBackend();
        await Task.Delay(200);
        StartBackend(arguments);
    }

    public async Task<bool> TaskRunAsync(string? configName)
    {
        try
        {
            object payload;
            if (string.IsNullOrEmpty(configName))
            {
                // 运行全部配置
                payload = new { };
            }
            else
            {
                // 从本地加载完整配置，发送给远程服务器
                var configPath = Path.Combine(DataPath.ConfigsDir, $"{configName}.json");
                if (!File.Exists(configPath))
                {
                    logger.LogError("Config file not found: {ConfigPath}", configPath);
                    return false;
                }

                var json = await File.ReadAllTextAsync(configPath);
                var config = JsonSerializer.Deserialize<TasksConfig>(json);
                if (config is null)
                {
                    logger.LogError("Failed to deserialize config: {ConfigName}", configName);
                    return false;
                }

                payload = new { Config = config, Persist = true };
            }

            var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
            var response = await Client.PostAsync($"{BaseUrl}/Task/run", content);

            if (response.IsSuccessStatusCode)
            {
                logger.LogInformation("Task run command sent (config: {Config})", configName ?? "all");
                return true;
            }

            logger.LogWarning("Task run failed: {StatusCode}", response.StatusCode);
            return false;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to call Task/run");
            return false;
        }
    }

    public async Task<bool> TaskStopAsync()
    {
        try
        {
            var response = await Client.PostAsync($"{BaseUrl}/Task/stop", null);

            if (response.IsSuccessStatusCode)
            {
                logger.LogInformation("Task stop command sent");
                return true;
            }

            logger.LogWarning("Task stop failed: {StatusCode}", response.StatusCode);
            return false;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to call Task/stop");
            return false;
        }
    }

    public Task<string> GetTaskStatusAsync()
    {
        logger.LogWarning("GetTaskStatus is not implemented for remote backend");
        return Task.FromResult(string.Empty);
    }

    public Task<byte[]> GetGameScreenshotBytesAsync()
    {
        logger.LogWarning("GetGameScreenshotBytes is not implemented for remote backend");
        return Task.FromResult(Array.Empty<byte>());
    }

    public Task<bool> SendInputAsync(string input)
    {
        logger.LogWarning("SendInput is not implemented for remote backend");
        return Task.FromResult(false);
    }

    public bool SendInput(string input)
    {
        logger.LogWarning("SendInput is not implemented for remote backend");
        return false;
    }

    public Task<bool> TaskSingleAsync(string taskName)
    {
        logger.LogWarning("TaskSingle is not implemented for remote backend");
        return Task.FromResult(false);
    }

    /// <summary>
    /// 连接到远程服务器：先同步当前任务状态，然后订阅 SSE 日志流。
    /// </summary>
    private async Task ConnectAndRunAsync(CancellationToken ct)
    {
        try
        {
            await SyncStatusAsync(ct);

            while (!ct.IsCancellationRequested)
            {
                try
                {
                    await SubscribeLogStreamAsync(ct);
                }
                catch (OperationCanceledException) when (ct.IsCancellationRequested)
                {
                    break;
                }
                catch (Exception ex)
                {
                    logger.LogWarning(ex, "SSE connection lost, reconnecting in 3s...");
                    Outputted?.Invoke("[RemoteBackend] 连接断开，3 秒后重连...");
                    await Task.Delay(3000, ct);
                }
            }
        }
        catch (OperationCanceledException)
        {
            // 正常退出
        }
        finally
        {
            _sseCts?.Dispose();
            _sseCts = null;
        }
    }

    /// <summary>调用 GET /Task/status 同步当前任务运行状态。</summary>
    private async Task SyncStatusAsync(CancellationToken ct)
    {
        try
        {
            var running = await Client.GetFromJsonAsync<bool>($"{BaseUrl}/Task/status", ct);
            IsTaskRunning = running;
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Failed to sync task status from remote server");
        }
    }

    /// <summary>订阅 GET /Task/logs/stream SSE 流，解析日志并更新任务状态。</summary>
    private async Task SubscribeLogStreamAsync(CancellationToken ct)
    {
        var request = new HttpRequestMessage(HttpMethod.Get, $"{BaseUrl}/Task/logs/stream");
        using var response = await Client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, ct);
        response.EnsureSuccessStatusCode();

        await using var stream = await response.Content.ReadAsStreamAsync(ct);
        using var reader = new StreamReader(stream);

        while (!ct.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(ct);
            if (line is null) break;

            if (!line.StartsWith("data: ")) continue;

            var data = line[6..];

            if (data.Contains(IBackendService.StartMarker))
                IsTaskRunning = true;
            else if (data.Contains(IBackendService.DoneMarker))
                IsTaskRunning = false;

            Outputted?.Invoke(data);
        }
    }
}

using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public abstract class LocalBackendService(ILogger<LocalBackendService> logger)
    : IBackendService
{
    private readonly SemaphoreSlim _commandLock = new(1, 1);
    private Process? _backendProcess;
    private TaskCompletionSource<string>? _outputTcs;
    public abstract string FileName { get; set; }
    public abstract string WorkingDirectory { get; set; }
    public abstract string MainArgument { get; set; }
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

    public bool SendInput(string input)
    {
        if (string.IsNullOrWhiteSpace(input))
        {
            logger.LogWarning("Attempted to send empty input to backend process.");
            return false;
        }

        if (_backendProcess == null || _backendProcess.HasExited)
        {
            logger.LogWarning("Attempted to send input to backend process, but it is not running. Input: {Input}",
                input);
            Outputted?.Invoke($"发送失败: 进程未运行（输入: {input}）");
            return false;
        }

        try
        {
            logger.LogInformation("Sending input to backend process: {Input}", input);
            _backendProcess.StandardInput.WriteLine(input);
            return true;
        }
        catch (IOException e)
        {
            logger.LogError(e, "Fail to send input to backend process: {Message}", e.Message);
            Outputted?.Invoke($"发送失败: {e.Message}（输入: {input}）");
            return false;
        }
    }

    public async Task<bool> SendInputAsync(string input)
    {
        if (string.IsNullOrWhiteSpace(input))
        {
            logger.LogWarning("Attempted to send empty input to backend process.");
            return false;
        }

        if (_backendProcess == null || _backendProcess.HasExited)
        {
            logger.LogWarning("Attempted to send input to backend process, but it is not running. Input: {Input}",
                input);
            Outputted?.Invoke($"发送失败: 进程未运行（输入: {input}）");
            return false;
        }

        try
        {
            logger.LogInformation("Sending input to backend process: {Input}", input);
            await _backendProcess.StandardInput.WriteLineAsync(input);
            return true;
        }
        catch (IOException e)
        {
            logger.LogError(e, "Fail to send input to backend process: {Message}", e.Message);
            Outputted?.Invoke($"发送失败: {e.Message}（输入: {input}）");
            return false;
        }
    }

    public void StartBackend(string arguments)
    {
        if (_backendProcess is not null) return;
        if (!File.Exists(FileName))
        {
            logger.LogError("Backend executable not found: {FileName}", FileName);
            Outputted?.Invoke($"启动失败: 未找到后端可执行文件（路径: {FileName}）");
            return;
        }

        var fullArguments = $"{MainArgument} {arguments}".Trim();
        logger.LogInformation("Starting backend {fileName} with arguments: {Arguments}", FileName, fullArguments);
        try
        {
            _backendProcess = new Process();
            _backendProcess.StartInfo = new ProcessStartInfo
            {
                UseShellExecute = false,
                FileName = FileName,
                Arguments = fullArguments,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                WorkingDirectory = WorkingDirectory
            };
            _backendProcess.EnableRaisingEvents = true; // 启用Exited事件
            _backendProcess.OutputDataReceived += OnBackendProcessOutputDataReceived;
            _backendProcess.ErrorDataReceived += OnBackendProcessErrorDataReceived;
            _backendProcess.Exited += OnBackendProcessExited;

            _backendProcess.Start();
            _backendProcess.BeginOutputReadLine();
            _backendProcess.BeginErrorReadLine();
            logger.LogInformation("Backend process started successfully (PID: {Pid})", _backendProcess.Id);
        }
        catch (Exception e)
        {
            logger.LogError(e, "Fail to start SRA: {Message}", e.Message);
            Outputted?.Invoke($"启动失败: {e.Message}");
            CleanupProcessResources();
        }
    }

    public void StopBackend()
    {
        if (_backendProcess == null) return;
        try
        {
            if (_backendProcess.HasExited) return;
            logger.LogInformation("Stopping backend (PID: {Pid})", _backendProcess.Id);
            // 优先发送停止命令，优雅退出）
            SendInput("exit");
            // 等待1秒，若未退出则强制终止
            if (_backendProcess.WaitForExit(1000)) return;
            _backendProcess.Kill();
            logger.LogWarning("Terminating backend process (PID: {Pid})", _backendProcess.Id);
        }
        catch (Exception e)
        {
            logger.LogError(e, "Fail to stop backend process: {Message}", e.Message);
        }
    }

    public async Task RestartBackendAsync(string arguments)
    {
        logger.LogInformation("Restarting backend process.");
        StopBackend();
        await Task.Delay(200);
        StartBackend(arguments);
    }

    public Task<bool> TaskRunAsync(string? configName)
    {
        return SendInputAsync(string.IsNullOrEmpty(configName) ? "task run" : $"task run {configName}");
    }

    public Task<bool> TaskSingleAsync(string taskName, string? configName)
    {
        return SendInputAsync(string.IsNullOrEmpty(configName) 
            ? $"task single {taskName}"
            : $"task single {taskName} --config {configName}");
    }

    public Task<bool> TaskStopAsync()
    {
        return SendInputAsync("task stop");
    }

    public Task<string?> TaskListAsync()
    {
        return SendInputAndWaitOutputAsync("task list --json");
    }

    public async Task<R> GetTaskStatusAsync()
    {
        return await SendInputAndWaitObjectAsync("task status --json") ?? new R(false, "No response from backend");
    }

    public async Task<Strategy[]> GetStrategiesAsync()
    {
        return await SendInputAndWaitObjectAsync<Strategy[]>("strategy list --json") ?? [];
    }

    public async Task<TpTask[]> GetTpConfigAsync()
    {
        var res = await SendInputAndWaitObjectAsync<Dictionary<string, TpTask>>("tpconfig --json");
        return res is null ? [] : [.. res.Values];
    }

    public async Task<(string Message, byte[])> GetGameScreenshotBytesAsync()
    {
        var screenshotPath = Path.Combine(WorkingDirectory, "screenshot.png");
        var param = new
        {
            save_path = screenshotPath,
            background = true,
            resize = new[] { 1280, 720 }
        };
        var result = await SendInputAndWaitObjectAsync($"operator call screenshot '{JsonSerializer.Serialize(param)}' --json");
        switch (result)
        {
            case null:
                logger.LogError("Failed to create screenshot: No response from backend.");
                return ("No response from backend.", []);
            case { Success: true }:
                var screenshotBytes = await File.ReadAllBytesAsync(screenshotPath);
                return (result.Message, screenshotBytes);
            default:
                logger.LogError("Failed to create screenshot.");
                return (result.Message, []);
        }
    }

    public async Task<ExtensionInfo[]> GetExtensionsAsync()
    {
        return await SendInputAndWaitObjectAsync<ExtensionInfo[]>("extension list --json") ?? [];
    }

    public async Task<ExtensionSchema?> GetExtensionSchemaAsync(string extensionId)
    {
        return await SendInputAndWaitObjectAsync<ExtensionSchema>($"extension schema {extensionId} --json");
    }

    public async Task<string?> GetExtensionConfigAsync(string extensionId)
    {
        var obj = await SendInputAndWaitObjectAsync<object>($"extension config get {extensionId} --json");
        return obj == null ? null : JsonSerializer.Serialize(obj);
    }

    public async Task<string?> SendInputAndWaitOutputAsync(string command)
    {
        await _commandLock.WaitAsync();
        try
        {
            if (_backendProcess == null || _backendProcess.HasExited)
            {
                logger.LogWarning(
                    "Attempted to send command to backend process, but it is not running. Command: {Command}", command);
                return null;
            }

            var tcs = new TaskCompletionSource<string>();
            _outputTcs = tcs;
            if (await SendInputAsync(command)) return await tcs.Task.WaitAsync(TimeSpan.FromSeconds(10));
            _outputTcs = null;
            return null;
        }
        catch (TimeoutException)
        {
            logger.LogError("Command timed out: {Command}", command);
            _outputTcs = null;
            return null;
        }
        catch (OperationCanceledException)
        {
            logger.LogWarning("Command canceled: {Command}", command);
            return null;
        }
        finally
        {
            _commandLock.Release();
        }
    }

    public async Task<T?> SendInputAndWaitObjectAsync<T>(string command)
    {
        var output = await SendInputAndWaitOutputAsync(command);
        if (output == null) return default;
        try
        {
            var response = JsonSerializer.Deserialize<R<T>>(output, options: JsonSerializerOptions.Web);
            if (response is { Success: true })
                return response.Data;
        }
        catch (JsonException ex)
        {
            logger.LogError(ex, "Failed to deserialize JSON response for command: {Command}", command);
        }
        return default;
    }

    public async Task<R?> SendInputAndWaitObjectAsync(string command)
    {
        var output = await SendInputAndWaitOutputAsync(command);
        if (output == null) return null;
        try
        {
            return JsonSerializer.Deserialize<R>(output, options: JsonSerializerOptions.Web);
        }
        catch (JsonException ex)
        {
            logger.LogError(ex, "Failed to deserialize JSON response for command: {Command}", command);
        }
        return null;
    }

    public Task<R?> OperatorCallAsync(string method, object? parameters)
    {
        var command = $"operator call {method} '{JsonSerializer.Serialize(parameters)}' --json";
        return SendInputAndWaitObjectAsync(command);
    }
    
    private void OnBackendProcessExited(object? sender, EventArgs e)
    {
        var processId = _backendProcess?.Id ?? -1;
        var exitCode = _backendProcess?.ExitCode ?? -1;
        logger.LogInformation("Process exited (PID: {Pid}, Exit Code: {ExitCode})", processId, exitCode);

        IsTaskRunning = false;
        Outputted?.Invoke($"进程已退出（PID: {processId}，退出代码为: {exitCode}）");

        // 清理资源
        CleanupProcessResources();
    }

    private void OnBackendProcessOutputDataReceived(object _, DataReceivedEventArgs args)
    {
        if (string.IsNullOrEmpty(args.Data)) return;

        Outputted?.Invoke(args.Data);

        // 完成等待中的输出请求
        if (_outputTcs?.TrySetResult(args.Data) == true)
            _outputTcs = null; // 释放引用
    }

    private void OnBackendProcessErrorDataReceived(object _, DataReceivedEventArgs args)
    {
        if (string.IsNullOrEmpty(args.Data)) return;

        // 更新运行状态
        if (args.Data.Contains(IBackendService.StartMarker))
            IsTaskRunning = true;
        else if (args.Data.Contains(IBackendService.DoneMarker))
            IsTaskRunning = false;

        Outputted?.Invoke(args.Data);
    }

    private void CleanupProcessResources()
    {
        if (_backendProcess == null) return;

        _backendProcess.OutputDataReceived -= OnBackendProcessOutputDataReceived;
        _backendProcess.ErrorDataReceived -= OnBackendProcessErrorDataReceived;
        _backendProcess.Exited -= OnBackendProcessExited;
        _backendProcess.Dispose();
        _backendProcess = null;
        IsTaskRunning = false;

        _outputTcs?.TrySetCanceled();
        _outputTcs = null;
    }
}
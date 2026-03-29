using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using Microsoft.Extensions.Logging;

namespace SRAFrontend.Services;

public abstract partial class LocalBackendService(ILogger<LocalBackendService> logger) : ObservableObject, IBackendService
{
    private Process? _backendProcess;
    public abstract string FileName { get; set; }
    public abstract string WorkingDirectory { get; set; }
    public abstract string MainArgument { get; set; }
    public event Action<string>? Outputted;
    [ObservableProperty] private bool _isTaskRunning;
    public bool SendInput(string input)
    {
        if (string.IsNullOrWhiteSpace(input))
        {
            logger.LogWarning("Attempted to send empty input to backend process.");
            return false;
        }

        if (_backendProcess == null || _backendProcess.HasExited)
        {
            logger.LogWarning("Attempted to send input to backend process, but it is not running. Input: {Input}", input);
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

    public void StartBackend(string arguments)
    {
        if (_backendProcess is not null) return;
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
            Dispatcher.UIThread.Post(() => Outputted?.Invoke($"启动失败: {e.Message}"));
            CleanupProcessResources();
        }
        
    }

    private void OnBackendProcessExited(object? sender, EventArgs e)
    {
        var processId = _backendProcess?.Id ?? -1;
        var exitCode = _backendProcess?.ExitCode ?? -1;
        logger.LogInformation("Process exited (PID: {Pid}, Exit Code: {ExitCode})", processId, exitCode);

        Dispatcher.UIThread.Post(() =>
        {
            IsTaskRunning = false;
            Outputted?.Invoke($"进程已退出（PID: {processId}，退出代码为: {exitCode}）");
        });

        // 清理资源
        CleanupProcessResources();
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

    public bool TaskRun(string? configName)
    {
        return SendInput(string.IsNullOrEmpty(configName) ? "task run" : $"task run {configName}");
    }

    public bool TaskSingle(string taskName)
    {
        return SendInput($"task single {taskName}");
    }

    public bool TaskStop()
    {
        return SendInput("task stop");
    }

    private void OnBackendProcessOutputDataReceived(object _, DataReceivedEventArgs args)
    {
        if (string.IsNullOrEmpty(args.Data)) return;

        Dispatcher.UIThread.Post(() =>
        {
            // 更新运行状态
            if (args.Data.Contains(IBackendService.StartMarker))
                IsTaskRunning = true;
            else if (args.Data.Contains(IBackendService.DoneMarker))
                IsTaskRunning = false;

            Outputted?.Invoke(args.Data);
        });
    }
    
    private void OnBackendProcessErrorDataReceived(object _, DataReceivedEventArgs args)
    {
        if (string.IsNullOrEmpty(args.Data)) return;

        Dispatcher.UIThread.Post(() =>
        {
            Outputted?.Invoke(args.Data);
        });
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
    }
}
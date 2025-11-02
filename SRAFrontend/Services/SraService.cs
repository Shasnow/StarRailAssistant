using System;
using System.Diagnostics;
using System.Text;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using Microsoft.Extensions.Logging;

namespace SRAFrontend.Services;

public partial class SraService : ObservableObject, IDisposable
{
    private readonly ILogger _logger;
    private readonly StringBuilder _outputBuffer = new();
    private readonly Process _sraProcess;
    private bool _isDisposed;
    [ObservableProperty] private bool _isRunning;
    [ObservableProperty] private string _output = "后端未启动。";

    public SraService(ILogger<SraService> logger)
    {
        _logger = logger;
        _sraProcess = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = "SRA-cli.exe",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                RedirectStandardInput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            }
        };
        _sraProcess.OutputDataReceived += OnSraProcessOutputDataReceived;
        _sraProcess.ErrorDataReceived += OnSraProcessErrorDataReceived;
        StartSraProcess("--inline");
    }

    private void OnSraProcessErrorDataReceived(object _, DataReceivedEventArgs args)
    {
        Dispatcher.UIThread.Post(() => { _outputBuffer.AppendLine(args.Data); });
    }

    private void OnSraProcessOutputDataReceived(object _, DataReceivedEventArgs args)
    {
        if (args.Data == null) return;
        // 通过 Dispatcher 切换到 UI 线程更新属性
        Dispatcher.UIThread.Post(() =>
        {
            if (args.Data.Contains("[Start]")) IsRunning = true;
            if (args.Data.Contains("[Done]")) IsRunning = false;
            _outputBuffer.AppendLine(args.Data);
            Output = _outputBuffer.ToString();
        });
    }

    private void StartSraProcess(string arguments)
    {
        _sraProcess.StartInfo.Arguments = arguments;
        try
        {
            _sraProcess.Start();
            _outputBuffer.Clear();
            Output = "";
            _sraProcess.BeginOutputReadLine();
            _sraProcess.BeginErrorReadLine();
        }
        catch (Exception e)
        {
            _logger.LogError("Failed to start SRA process: {Message}", e.Message);
        }
    }

    public void StopSraProcess()
    {
        try
        {
            if (!_sraProcess.HasExited) _sraProcess.Kill();
        }
        catch (InvalidOperationException e)
        {
            _logger.LogError("Failed to stop SRA process: {Message}", e.Message);
        }
    }

    public void SendInput(string input)
    {
        if (input == "") return;
        _logger.LogInformation("SendInput to SRA-cli: {Input}", input);
        if (!_sraProcess.HasExited) _sraProcess.StandardInput.WriteLine(input);
    }

    public void TaskRun(string? configName)
    {
        SendInput(string.IsNullOrEmpty(configName) ? "task run" : $"task run {configName}");
    }

    ~SraService() // 终结器（防错机制，确保非托管资源释放）
    {
        Dispose(false);
    }

    public void Dispose()
    {
        Dispose(true);
        GC.SuppressFinalize(this); // 告诉GC不需要调用终结器
    }

    private void Dispose(bool disposing)
    {
        // 防止重复释放
        if (_isDisposed)
            return;

        // 释放托管资源（仅在手动调用Dispose时执行）
        if (disposing)
        {
            // 解绑事件（避免回调被触发时访问已释放资源）
            _sraProcess.OutputDataReceived -= OnSraProcessOutputDataReceived;
            _sraProcess.ErrorDataReceived -= OnSraProcessErrorDataReceived;

            // 停止进程（若仍在运行）
            StopSraProcess();
        }

        // 释放非托管资源（Process内部的句柄等）
        if (!_sraProcess.HasExited)
            try
            {
                _sraProcess.Kill(); // 强制终止（若StopSraProcess未成功）
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "释放时终止进程失败");
            }

        _sraProcess.Dispose(); // 释放Process的所有资源

        _isDisposed = true;
    }
}
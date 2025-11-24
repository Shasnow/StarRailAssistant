using System;
using System.Diagnostics;
using System.IO;
using Avalonia.Collections;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;

namespace SRAFrontend.Services;

// 提取常量，提高可维护性
internal static class SraServiceConstants
{
    public const string BackendNotStartedText = "后端未启动。";
    public const string StartMarker = "[Start]";
    public const string DoneMarker = "[Done]";
    public const int MaxOutputLines = 1000; // 可选: 日志行数限流
}

public partial class SraService(ILogger<SraService> logger)
    : ObservableObject, IDisposable
{
    private readonly ILogger _logger = logger;
    private bool _isDisposed;

    // 简化 ObservableProperty 初始化
    [ObservableProperty] private bool _isRunning;

    [ObservableProperty] private AvaloniaList<string> _outputLines = [SraServiceConstants.BackendNotStartedText];

    private Process? _sraProcess;

    /// <summary>
    ///     启动SRA进程（线程安全）
    /// </summary>
    /// <param name="arguments">命令行参数</param>
    public void StartSraProcess(string arguments)
    {
        // 已运行则直接返回
        if (IsRunning)
        {
            _logger.LogInformation("SRA is already running.");
            return;
        }

        // 校验核心文件路径
        var mainPyPath = Path.Combine(Environment.CurrentDirectory, "SRA-cli.exe");
        if (!File.Exists(mainPyPath))
        {
            _logger.LogError("Could not find SRA-cli.exe at path: {Path}", mainPyPath);
            var errorMsg = $"无法找到文件 SRA-cli.exe，请检查安装完整性。\n路径: {mainPyPath}";
            OutputLines.Add(errorMsg);
            return;
        }

        // 清理之前的进程资源（若有）
        if (_sraProcess != null)
        {
            _sraProcess.Dispose();
            _sraProcess = null;
        }

        try
        {
            // 优化: 使用安全的参数传递（避免字符串拼接导致的命令注入）
            var safeArguments = $"\"{mainPyPath}\" {EscapeCommandLineArgument(arguments)}";
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

            // 绑定事件（包含Exited事件）
            _sraProcess.OutputDataReceived += OnSraProcessOutputDataReceived;
            _sraProcess.ErrorDataReceived += OnSraProcessErrorDataReceived;
            _sraProcess.Exited += OnSraProcessExited;
            _sraProcess.EnableRaisingEvents = true; // 启用Exited事件

            // 启动进程
            _sraProcess.Start();
            _logger.LogInformation("Successfully start SRA with command: {Arguments}", safeArguments);

            OutputLines.Clear();

            _sraProcess.BeginOutputReadLine();
            _sraProcess.BeginErrorReadLine();
        }
        catch (Exception e)
        {
            _logger.LogError(e, "Fail to start SRA: {Message}", e.Message);
            Dispatcher.UIThread.Post(() => OutputLines.Add($"启动失败: {e.Message}"));
            // 异常时清理资源
            _sraProcess?.Dispose();
            _sraProcess = null;
        }
    }

    /// <summary>
    ///     重启SRA进程
    /// </summary>
    public void RestartSraProcess(string arguments)
    {
        _logger.LogInformation("Restarting SRA process.");
        StopSraProcess();
        StartSraProcess(arguments);
    }

    /// <summary>
    ///     停止SRA进程
    /// </summary>
    public void StopSraProcess()
    {
        if (_sraProcess == null)
        {
            _logger.LogInformation("SRA is not running.");
            return;
        }

        try
        {
            if (_sraProcess.HasExited) return;
            _logger.LogInformation("Stopping SRA (PID: {Pid})", _sraProcess.Id);
            // 优先发送停止命令，优雅退出）
            SendInput("exit");
            // 等待1秒，若未退出则强制终止
            if (_sraProcess.WaitForExit(1000)) return;
            _sraProcess.Kill();
            _logger.LogWarning("Terminating SRA (PID: {Pid})", _sraProcess.Id);
        }
        catch (InvalidOperationException e)
        {
            _logger.LogError(e, "Fail to stop SRA: {Message}", e.Message);
        }
        finally
        {
            // 无论是否成功，都清理进程资源
            CleanupProcessResources();
        }
    }

    /// <summary>
    ///     发送输入到进程
    /// </summary>
    public void SendInput(string input)
    {
        if (string.IsNullOrWhiteSpace(input))
        {
            _logger.LogWarning("Attempted to send empty input to SRA process.");
            return;
        }

        if (_sraProcess == null || _sraProcess.HasExited)
        {
            _logger.LogWarning("Attempted to send input to SRA process, but it is not running. Input: {Input}", input);
            OutputLines.Add($"发送失败: 进程未运行（输入: {input}）");
            return;
        }

        try
        {
            _logger.LogInformation("Sending input to SRA process: {Input}", input);
            _sraProcess.StandardInput.WriteLine(input);
        }
        catch (IOException e)
        {
            _logger.LogError(e, "Fail to send input to SRA process: {Message}", e.Message);
            OutputLines.Add($"发送失败: {e.Message}（输入: {input}）");
        }
    }

    public void TaskRun(string? configName)
    {
        SendInput(string.IsNullOrEmpty(configName) ? "task run" : $"task run {configName}");
    }

    public void TaskStop()
    {
        SendInput("task stop");
    }

    #region 辅助方法

    /// <summary>
    ///     转义命令行参数（避免注入风险）
    /// </summary>
    private static string EscapeCommandLineArgument(string argument)
    {
        // 若参数包含空格、引号等特殊字符，需要添加引号包裹
        if (!argument.Contains(' ') && !argument.Contains('"') && !argument.Contains('\\')) return argument;
        // 转义双引号和反斜杠
        argument = argument.Replace("\\", "\\\\").Replace("\"", "\\\"");
        return $"\"{argument}\"";
    }

    #endregion

    #region 进程事件处理

    private void OnSraProcessOutputDataReceived(object _, DataReceivedEventArgs args)
    {
        if (string.IsNullOrEmpty(args.Data)) return;

        Dispatcher.UIThread.Post(() =>
        {
            // 更新运行状态
            if (args.Data.Contains(SraServiceConstants.StartMarker))
                IsRunning = true;
            else if (args.Data.Contains(SraServiceConstants.DoneMarker))
                IsRunning = false;

            // 日志限流: 超过最大行数时移除最早的
            if (OutputLines.Count >= SraServiceConstants.MaxOutputLines)
                OutputLines.RemoveAt(0);

            OutputLines.Add(args.Data);
        });
    }

    private void OnSraProcessErrorDataReceived(object _, DataReceivedEventArgs args)
    {
        if (string.IsNullOrEmpty(args.Data)) return;

        Dispatcher.UIThread.Post(() =>
        {
            // 错误日志标红（如果UI支持，可在这里添加标记）
            OutputLines.Add(args.Data);
        });
    }

    /// <summary>
    ///     进程退出时触发（正常/异常退出）
    /// </summary>
    private void OnSraProcessExited(object? _, EventArgs __)
    {
        var processId = _sraProcess?.Id ?? -1;
        var exitCode = _sraProcess?.ExitCode ?? -1;
        _logger.LogInformation("Process exited (PID: {Pid}, Exit Code: {ExitCode})", processId, exitCode);

        Dispatcher.UIThread.Post(() =>
        {
            IsRunning = false;
            OutputLines.Add($"进程已退出（PID: {processId}，退出代码为: {exitCode}）");
        });

        // 清理资源
        CleanupProcessResources();
    }

    #endregion

    #region 资源清理

    /// <summary>
    ///     清理进程相关资源（解绑事件+释放进程对象，仅在手动Dispose时调用）
    /// </summary>
    private void CleanupProcessResources()
    {
        if (_sraProcess == null) return;

        // 1. 清理托管资源：解绑事件（仅手动释放时需要，避免内存泄漏）
        _sraProcess.OutputDataReceived -= OnSraProcessOutputDataReceived;
        _sraProcess.ErrorDataReceived -= OnSraProcessErrorDataReceived;
        _sraProcess.Exited -= OnSraProcessExited;

        // 2. 清理非托管资源：释放进程对象
        DisposeProcess();
    }

    /// <summary>
    ///     仅释放进程的非托管资源（进程句柄），不处理托管资源
    /// </summary>
    private void DisposeProcess()
    {
        if (_sraProcess == null) return;

        try
        {
            // 确保进程终止（非托管资源释放的关键）
            if (_sraProcess.HasExited) return;
            _sraProcess.Kill();
            _sraProcess.WaitForExit(1000); // 等待进程退出
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "释放进程非托管资源时失败（PID: {Pid}）", _sraProcess.Id);
        }
        finally
        {
            _sraProcess.Dispose(); // 释放进程句柄（核心非托管资源）
            _sraProcess = null;
            IsRunning = false;
        }
    }

    public void Dispose()
    {
        Dispose(true);
        GC.SuppressFinalize(this); // 手动释放后，禁止GC调用终结器
    }

    ~SraService()
    {
        Dispose(false); // GC触发，仅释放非托管资源
    }

    /// <summary>
    ///     标准IDisposable实现：根据disposing区分托管/非托管资源释放
    /// </summary>
    /// <param name="disposing">true=手动释放（托管+非托管），false=GC终结（仅非托管）</param>
    private void Dispose(bool disposing)
    {
        if (_isDisposed) return;
        if (disposing)
            // 手动释放：清理托管资源（事件解绑）+ 非托管资源（进程）
            CleanupProcessResources();
        else
            // GC终结：仅清理非托管资源（进程句柄），不访问托管资源（如事件）
            DisposeProcess();

        _isDisposed = true;
    }

    #endregion
}
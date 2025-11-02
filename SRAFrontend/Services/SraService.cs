using System;
using System.Diagnostics;
using CommunityToolkit.Mvvm.ComponentModel;
using Microsoft.Extensions.Logging;

namespace SRAFrontend.Services;

public partial class SraService : ObservableObject
{
    private readonly Process _sraProcess;
    [ObservableProperty] private bool _isRunning;
    [ObservableProperty] private string _output = "后端未启动。";
    private readonly ILogger _logger;

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
        _sraProcess.OutputDataReceived += (_, args) =>
        {
            if (args.Data == null) return;
            if (args.Data.Contains("[Start]")) IsRunning = true;
            if (args.Data.Contains("[Done]")) IsRunning = false;
            Output += args.Data + "\n";
        };
        _sraProcess.ErrorDataReceived += (_, args) =>
        {
            if (args.Data == null) return;
            Output += args.Data + "\n";
        };
        StartSraProcess("");
    }

    private void StartSraProcess(string arguments)
    {
        _sraProcess.StartInfo.Arguments = arguments;
        try
        {
            _sraProcess.Start();
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
}
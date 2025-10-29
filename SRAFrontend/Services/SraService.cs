using System;
using System.Diagnostics;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Services;

public partial class SraService : ObservableObject
{
    private readonly Process _sraProcess;
    [ObservableProperty] private bool _isRunning;
    [ObservableProperty] private string _output = "后端未启动。";

    public SraService()
    {
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
            if (args.Data.Contains("[Done]")) IsRunning = false;
            Output += args.Data + "\n";
        };
        _sraProcess.ErrorDataReceived += (_, args) =>
        {
            if (args.Data == null) return;
            Output += args.Data + "\n";
        };
        // StartSraProcess("");
    }

    private void StartSraProcess(string arguments)
    {
        _sraProcess.StartInfo.Arguments = arguments;
        Output = "";
        _sraProcess.Start();
        _sraProcess.BeginOutputReadLine();
        _sraProcess.BeginErrorReadLine();
    }

    public void StopSraProcess()
    {
        try
        {
            if (!_sraProcess.HasExited) _sraProcess.Kill();
        }
        catch (InvalidOperationException e)
        {
            Console.WriteLine(e);
        }
    }

    public void SendInput(string input)
    {
        if (input == "") return;
        if (!_sraProcess.HasExited) _sraProcess.StandardInput.WriteLine(input);
    }

    public void TaskRun(string? configName)
    {
        IsRunning = true;
        SendInput(string.IsNullOrEmpty(configName) ? "task run" : $"task run {configName}");
    }
}
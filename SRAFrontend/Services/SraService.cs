using System.Diagnostics;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Services;

public partial class SraService: ObservableObject
{
    [ObservableProperty]private string _output="";
    private readonly Process _sraProcess;
    public SraService()
    {
        _sraProcess=new Process
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
        _sraProcess.OutputDataReceived += (sender, args) =>
        {
            if (args.Data != null)
            {
                Output += args.Data + "\n";
            }
        };
        _sraProcess.ErrorDataReceived += (sender, args) =>
        {
            if (args.Data != null)
            {
                Output += args.Data + "\n";
            }
        };
        StartSraProcess("");
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
        if (!_sraProcess.HasExited)
        {
            _sraProcess.Kill();
        }
    }
    
    public void SendInput(string input)
    {
        if (input == "") return;
        if (!_sraProcess.HasExited)
        {
            _sraProcess.StandardInput.WriteLine(input);
        }
    }
}
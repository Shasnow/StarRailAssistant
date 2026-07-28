using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Threading.Tasks;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public interface IBackendService : INotifyPropertyChanged
{
    const string StartMarker = "[Start]";
    const string DoneMarker = "[Done]";
    bool IsTaskRunning { get; set; }
    event Action<string>? Outputted;
    bool SendInput(string input);
    Task<bool> SendInputAsync(string input);
    void StartBackend(string arguments);
    void StopBackend();
    Task RestartBackendAsync(string arguments);
    Task<bool> TaskRunAsync(string? configName);
    Task<bool> TaskSingleAsync(string taskName);
    Task<bool> TaskStopAsync();
    Task<string> GetTaskStatusAsync();
    Task<List<Strategy>> GetStrategiesAsync();
    Task<TpTask[]> GetTpConfigAsync();
    Task<byte[]> GetGameScreenshotBytesAsync();
}
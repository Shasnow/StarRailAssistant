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
    Task<string?> SendInputAndWaitOutputAsync(string command);
    Task<T?> SendInputAndWaitObjectAsync<T>(string command);
    Task<BackendResponse?> SendInputAndWaitObjectAsync(string command);
    void StartBackend(string arguments);
    void StopBackend();
    Task RestartBackendAsync(string arguments);
    Task<bool> TaskRunAsync(string? configName);
    Task<bool> TaskSingleAsync(string taskName, string? configName);
    Task<string?> TaskListAsync();
    Task<bool> TaskStopAsync();
    Task<string> GetTaskStatusAsync();
    Task<Strategy[]> GetStrategiesAsync();
    Task<TpTask[]> GetTpConfigAsync();
    Task<(string Message, byte[])> GetGameScreenshotBytesAsync();
    Task<ExtensionInfo[]> GetExtensionsAsync();
    Task<ExtensionSchema?> GetExtensionSchemaAsync(string extensionId);
    Task<string?> GetExtensionConfigAsync(string extensionId);
    Task<BackendResponse?> OperatorCallAsync(string method, object? parameters);
}

public record BackendResponse<T>(bool Success, string Message, T Data);
public record BackendResponse(bool Success, string Message, object? Data);
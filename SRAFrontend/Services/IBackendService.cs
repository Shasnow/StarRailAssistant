using System;
using System.ComponentModel;
using System.Threading.Tasks;

namespace SRAFrontend.Services;

public interface IBackendService: INotifyPropertyChanged
{
    const string StartMarker = "[Start]";
    const string DoneMarker = "[Done]";
    event Action<string>? Outputted;
    bool IsTaskRunning { get; set; }
    bool SendInput(string input);
    void StartBackend(string arguments);
    void StopBackend();
    Task RestartBackendAsync(string arguments);
    bool TaskRun(string? configName);
    bool TaskSingle(string taskName);
    bool TaskStop();
}
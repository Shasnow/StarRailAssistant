using System;
using System.ComponentModel;
using System.IO;
using System.Threading.Tasks;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class BackendServiceProxy(CliBackendService cliBackendService, PyBackendService pyBackendService,
    SettingsService settingsService) : IBackendService
{
    private IBackendService _currentBackend = cliBackendService;
    private string _lastStartArguments = string.Empty;

    public void Initialize()
    {
        // 初始化 Python 后端配置
        ApplyPythonSettings();

        var isUsingPython = Environment.GetCommandLineArgs().Contains("--use-python") ||
                            settingsService.Settings.Advanced is { IsDeveloperModeEnabled: true, IsPythonEnabled: true };

        _currentBackend = isUsingPython ? pyBackendService : cliBackendService;
        AttachToCurrentBackend();
        IsTaskRunning = _currentBackend.IsTaskRunning;

        // 监听设置变化，动态切换后端和更新 Python 配置
        settingsService.SettingsPropertyChanged += OnSettingsPropertyChanged;
    }

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
        return _currentBackend.SendInput(input);
    }

    public void StartBackend(string arguments)
    {
        _lastStartArguments = arguments;
        _currentBackend.StartBackend(arguments);
    }

    public void StopBackend()
    {
        _currentBackend.StopBackend();
    }

    public async Task RestartBackendAsync(string arguments)
    {
        _lastStartArguments = arguments;
        await _currentBackend.RestartBackendAsync(arguments);
    }

    public bool TaskRun(string? configName)
    {
        return _currentBackend.TaskRun(configName);
    }

    public bool TaskSingle(string taskName)
    {
        return _currentBackend.TaskSingle(taskName);
    }

    public bool TaskStop()
    {
        return _currentBackend.TaskStop();
    }

    private void ApplyPythonSettings()
    {
        var pythonPath = settingsService.Settings.Advanced.PythonPath;
        var mainPy = settingsService.Settings.Advanced.PythonMain;

        if (!string.IsNullOrWhiteSpace(pythonPath))
            pyBackendService.FileName = pythonPath;

        if (!string.IsNullOrWhiteSpace(mainPy))
        {
            pyBackendService.MainArgument = mainPy;
            pyBackendService.WorkingDirectory = Path.GetDirectoryName(mainPy) ?? Environment.CurrentDirectory;
        }
    }

    private void OnSettingsPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(AdvancedSettings.IsPythonEnabled))
        {
            var usePython = settingsService.Settings.Advanced.IsPythonEnabled;
            IBackendService target = usePython ? pyBackendService : cliBackendService;
            SetCurrentBackend(target);
        }

        if (e.PropertyName is nameof(AdvancedSettings.PythonPath) or nameof(AdvancedSettings.PythonMain))
            ApplyPythonSettings();
    }

    private void SetCurrentBackend(IBackendService backend)
    {
        if (ReferenceEquals(_currentBackend, backend)) return;

        _currentBackend.StopBackend();
        DetachFromCurrentBackend();
        _currentBackend = backend;
        AttachToCurrentBackend();
        IsTaskRunning = _currentBackend.IsTaskRunning;

        if (string.IsNullOrWhiteSpace(_lastStartArguments)) return;
        _currentBackend.StartBackend(_lastStartArguments);
    }

    private void AttachToCurrentBackend()
    {
        _currentBackend.Outputted += OnBackendOutputted;
        _currentBackend.PropertyChanged += OnBackendPropertyChanged;
    }

    private void DetachFromCurrentBackend()
    {
        _currentBackend.Outputted -= OnBackendOutputted;
        _currentBackend.PropertyChanged -= OnBackendPropertyChanged;
    }

    private void OnBackendOutputted(string message)
    {
        Outputted?.Invoke(message);
    }

    private void OnBackendPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(IsTaskRunning) || string.IsNullOrEmpty(e.PropertyName))
            IsTaskRunning = _currentBackend.IsTaskRunning;
    }
}

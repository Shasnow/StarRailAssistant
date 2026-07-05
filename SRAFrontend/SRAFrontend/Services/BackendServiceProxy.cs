using System;
using System.ComponentModel;
using System.IO;
using System.Threading.Tasks;
using Microsoft.Extensions.DependencyInjection;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class BackendServiceProxy(CliBackendService cliBackendService, PyBackendService pyBackendService,
    IServiceProvider serviceProvider, SettingsService settingsService) : IBackendService
{
    private RemoteBackendService? _remoteBackendService;
    private IBackendService _currentBackend = cliBackendService;
    private string _lastStartArguments = string.Empty;
    private bool _initialized;

    private void Initialize()
    {
        // 按需解析 RemoteBackendService（Server 端未注册时返回 null）
        _remoteBackendService = serviceProvider.GetService<RemoteBackendService>();

        // 初始化 Python 后端配置
        ApplyPythonSettings();
        // 初始化远程后端配置
        ApplyRemoteSettings();

        var adv = settingsService.Settings.Advanced;
        var isUsingPython = Environment.GetCommandLineArgs().Contains("--use-python") ||
                            adv is { IsDeveloperModeEnabled: true, IsPythonEnabled: true };
        var isUsingRemote = adv.IsRemoteEnabled && _remoteBackendService is not null;

        if (isUsingRemote)
            _currentBackend = _remoteBackendService!;
        else if (isUsingPython)
            _currentBackend = pyBackendService;
        else
            _currentBackend = cliBackendService;

        AttachToCurrentBackend();
        IsTaskRunning = _currentBackend.IsTaskRunning;

        // 监听设置变化，动态切换后端和更新配置
        settingsService.SettingsPropertyChanged += OnSettingsPropertyChanged;
        _initialized = true;
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

    public Task<bool> SendInputAsync(string input)
    {
        if (!_initialized) Initialize();
        return _currentBackend.SendInputAsync(input);
    }

    public bool SendInput(string input)
    {
        if (!_initialized) Initialize();
        return _currentBackend.SendInput(input);
    }

    public void StartBackend(string arguments)
    {
        if (!_initialized) Initialize();
        _lastStartArguments = arguments;
        _currentBackend.StartBackend(arguments);
    }

    public void StopBackend()
    {
        if (!_initialized) return;
        _currentBackend.StopBackend();
    }

    public Task RestartBackendAsync(string arguments)
    {
        if (!_initialized) Initialize();
        _lastStartArguments = arguments;
        return _currentBackend.RestartBackendAsync(arguments);
    }

    public Task<bool> TaskRunAsync(string? configName)
    {
        if (!_initialized) Initialize();
        return _currentBackend.TaskRunAsync(configName);
    }

    public Task<bool> TaskSingleAsync(string taskName)
    {
        if (!_initialized) Initialize();
        return _currentBackend.TaskSingleAsync(taskName);
    }

    public Task<bool> TaskStopAsync()
    {
        if (!_initialized) Initialize();
        return _currentBackend.TaskStopAsync();
    }

    public Task<string> GetTaskStatusAsync()
    {
        return _currentBackend.GetTaskStatusAsync();
    }

    public Task<byte[]> GetGameScreenshotBytesAsync()
    {
        return _currentBackend.GetGameScreenshotBytesAsync();
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

    private void ApplyRemoteSettings()
    {
        if (_remoteBackendService is null) return;
        var baseUrl = settingsService.Settings.Advanced.RemoteBaseUrl;
        if (!string.IsNullOrWhiteSpace(baseUrl))
            _remoteBackendService.BaseUrl = baseUrl;
    }

    private void OnSettingsPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(AdvancedSettings.IsRemoteEnabled) && _remoteBackendService is not null)
        {
            var useRemote = settingsService.Settings.Advanced.IsRemoteEnabled;
            IBackendService target = useRemote
                ? _remoteBackendService
                : settingsService.Settings.Advanced.IsPythonEnabled ? pyBackendService : cliBackendService;
            SetCurrentBackend(target);
        }

        if (e.PropertyName == nameof(AdvancedSettings.IsPythonEnabled))
        {
            var usePython = settingsService.Settings.Advanced.IsPythonEnabled;
            if (!settingsService.Settings.Advanced.IsRemoteEnabled)
            {
                IBackendService target = usePython ? pyBackendService : cliBackendService;
                SetCurrentBackend(target);
            }
        }

        if (e.PropertyName is nameof(AdvancedSettings.PythonPath) or nameof(AdvancedSettings.PythonMain))
            ApplyPythonSettings();

        if (e.PropertyName == nameof(AdvancedSettings.RemoteBaseUrl))
            ApplyRemoteSettings();
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

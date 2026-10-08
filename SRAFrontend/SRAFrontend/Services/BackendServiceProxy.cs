using System;
using System.ComponentModel;
using System.Threading.Tasks;
using Microsoft.Extensions.DependencyInjection;
using SRAFrontend.Data;
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

        // 初始化自定义后端配置
        ApplyBackendSettings();
        // 初始化远程后端配置
        ApplyRemoteSettings();

        var adv = settingsService.Settings.Advanced;
        var isUsingPython = Environment.GetCommandLineArgs().Contains("--use-python") ||
                            adv is { IsDeveloperModeEnabled: true, IsCustomBackendEnabled: true };
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

    public Task<T?> SendInputAndWaitObjectAsync<T>(string command)
    {
        return _currentBackend.SendInputAndWaitObjectAsync<T>(command);
    }

    public Task<R?> SendInputAndWaitObjectAsync(string command)
    {
        return _currentBackend.SendInputAndWaitObjectAsync(command);
    }

    public void StartBackend(string arguments)
    {
        if (!_initialized) Initialize();
        _lastStartArguments = arguments;
        _currentBackend.StartBackend(arguments);
    }

    public void StopBackend()
    {
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
        return _currentBackend.TaskRunAsync(configName);
    }

    public Task<bool> TaskSingleAsync(string taskName, string? configName)
    {
        return _currentBackend.TaskSingleAsync(taskName, configName);
    }
    
    

    public Task<string?> TaskListAsync()
    {
        return _currentBackend.TaskListAsync();
    }

    public Task<bool> TaskStopAsync()
    {
        return _currentBackend.TaskStopAsync();
    }

    public Task<R> GetTaskStatusAsync()
    {
        return _currentBackend.GetTaskStatusAsync();
    }

    public Task<Strategy[]> GetStrategiesAsync()
    {
        return _currentBackend.GetStrategiesAsync();
    }

    public Task<R?> InstallStrategyAsync(string filePath)
    {
        return _currentBackend.InstallStrategyAsync(filePath);
    }

    public Task<TpTask[]> GetTpConfigAsync()
    {
        return _currentBackend.GetTpConfigAsync();
    }

    public Task<(string Message, byte[])> GetGameScreenshotBytesAsync()
    {
        return _currentBackend.GetGameScreenshotBytesAsync();
    }

    public Task<ExtensionInfo[]> GetExtensionsAsync()
    {
        return _currentBackend.GetExtensionsAsync();
    }

    public Task<ExtensionSchema?> GetExtensionSchemaAsync(string extensionId)
    {
        return _currentBackend.GetExtensionSchemaAsync(extensionId);
    }

    public Task<string?> GetExtensionConfigAsync(string extensionId)
    {
        return _currentBackend.GetExtensionConfigAsync(extensionId);
    }

    public Task<string?> SendInputAndWaitOutputAsync(string command)
    {
        return _currentBackend.SendInputAndWaitOutputAsync(command);
    }

    public Task<R?> OperatorCallAsync(string method, object? parameters)
    {
        return _currentBackend.OperatorCallAsync(method, parameters);
    }

    private void ApplyBackendSettings()
    {
        var adv = settingsService.Settings.Advanced;

        // 命令/可执行文件：支持引号包裹的路径
        var command = adv.CustomBackendCommand.Trim().Trim('"');
        var arguments = adv.CustomBackendArguments.Trim();

        // 留空时回退到内置 python 运行 main.py（保持原默认行为）
        pyBackendService.FileName = command.Length == 0 ? DataPath.PythonExe : command;
        pyBackendService.MainArgument = command.Length == 0 && arguments.Length == 0 ? "main.py" : arguments;

        pyBackendService.WorkingDirectory = string.IsNullOrWhiteSpace(adv.CustomBackendWorkingDirectory)
            ? Environment.CurrentDirectory
            : adv.CustomBackendWorkingDirectory;
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
                : settingsService.Settings.Advanced.IsCustomBackendEnabled ? pyBackendService : cliBackendService;
            SetCurrentBackend(target);
        }

        if (e.PropertyName == nameof(AdvancedSettings.IsCustomBackendEnabled))
        {
            var useCustomBackend = settingsService.Settings.Advanced.IsCustomBackendEnabled;
            if (!settingsService.Settings.Advanced.IsRemoteEnabled)
            {
                IBackendService target = useCustomBackend ? pyBackendService : cliBackendService;
                SetCurrentBackend(target);
            }
        }

        if (e.PropertyName is nameof(AdvancedSettings.CustomBackendCommand) or nameof(AdvancedSettings.CustomBackendArguments)
            or nameof(AdvancedSettings.CustomBackendWorkingDirectory))
            ApplyBackendSettings();

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

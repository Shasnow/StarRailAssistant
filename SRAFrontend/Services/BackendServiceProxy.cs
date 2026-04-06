using System;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class BackendServiceProxy : IBackendService
{
    private readonly CliBackendService _cliBackendService;
    private readonly PyBackendService _pyBackendService;
    private readonly SettingsService _settingsService;

    private IBackendService _currentBackend;

    private bool _isTaskRunning;
    private string _lastStartArguments = string.Empty; // 记录最近一次 StartBackend/RestartBackend 使用的参数

    public BackendServiceProxy(CliBackendService cliBackendService, PyBackendService pyBackendService,
        SettingsService settingsService)
    {
        _cliBackendService = cliBackendService;
        _pyBackendService = pyBackendService;
        _settingsService = settingsService;

        // 初始化 Python 后端配置
        ApplyPythonSettings();
        var isUsingPython = Environment.GetCommandLineArgs().Contains("--use-python") || _settingsService.Settings is
            { IsDeveloperMode: true, IsUsingPython: true };
        // 根据设置决定初始后端
        _currentBackend = isUsingPython
            ? _pyBackendService
            : _cliBackendService;
        AttachToCurrentBackend();
        // 初始化镜像状态
        IsTaskRunning = _currentBackend.IsTaskRunning;

        // 监听设置变化，动态切换后端和更新 Python 配置
        _settingsService.Settings.PropertyChanged += OnSettingsPropertyChanged;
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    public event Action<string>? Outputted;

    public bool IsTaskRunning
    {
        get => _isTaskRunning;
        set
        {
            if (_isTaskRunning == value) return;
            _isTaskRunning = value;
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
        // 将当前 Settings 中的 Python 配置同步到 PyBackendService
        var pythonPath = _settingsService.Settings.PythonPath;
        var mainPy = _settingsService.Settings.PythonMainPy;

        if (!string.IsNullOrWhiteSpace(pythonPath))
            _pyBackendService.FileName = pythonPath;

        if (!string.IsNullOrWhiteSpace(mainPy))
        {
            _pyBackendService.MainArgument = mainPy;
            _pyBackendService.WorkingDirectory = Path.GetDirectoryName(mainPy) ?? Environment.CurrentDirectory;
        }
    }

    private void OnSettingsPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        // 后端选择
        if (e.PropertyName == nameof(Settings.IsUsingPython))
        {
            var usePython = _settingsService.Settings.IsUsingPython;
            IBackendService target = usePython ? _pyBackendService : _cliBackendService;
            SetCurrentBackend(target);
        }

        // Python 配置变更时，同步到 PyBackendService
        if (e.PropertyName is nameof(Settings.PythonPath) or nameof(Settings.PythonMainPy)) ApplyPythonSettings();
    }

    // 允许后续切换后端的扩展点
    private void SetCurrentBackend(IBackendService backend)
    {
        if (ReferenceEquals(_currentBackend, backend)) return;

        // 切换前确保旧后端已停止，避免两个后端同时跑
        _currentBackend.StopBackend();
        DetachFromCurrentBackend();
        _currentBackend = backend;
        AttachToCurrentBackend();
        IsTaskRunning = _currentBackend.IsTaskRunning;

        // 如果之前已经有启动参数记录，则在切换后自动启动新后端
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
            // 同步当前后端的运行状态到代理自身
            IsTaskRunning = _currentBackend.IsTaskRunning;

        // 如果未来代理公开更多与后端同名的属性，可在此决定是否转发其它属性变更
    }
}
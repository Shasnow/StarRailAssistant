using System;
using System.Collections.Concurrent;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia.Collections;
using Avalonia.Controls;
using Avalonia.Platform.Storage;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.Desktop.ViewModels;

public partial class ConsolePageViewModel : PageViewModel
{
    private const int MaxConsoleLines = 1000;
    private readonly IBackendService _backendService;
    private readonly ConcurrentQueue<string> _consoleLines = new();

    private readonly string[] _levelPrefixes = ["TRACE", "DEBUG", "INFO", "WARN", "ERROR"];
    private readonly ILogger<ConsolePageViewModel> _logger;
    private readonly CommonModel _commonModel;
    private readonly SettingsService _settingsService;

    [ObservableProperty]
    private AvaloniaList<bool> _filterOptions = [false, false, true, true, true]; // TRACE, DEBUG, INFO, WARN, ERROR

    [ObservableProperty]
    private bool _isExporting; // 日志导出进行中标志

    public TopLevel? TopLevelObject { get; set; }

    public ConsolePageViewModel(IBackendService backendService, SettingsService settingsService,
        CommonModel commonModel, ILogger<ConsolePageViewModel> logger) : base(
        PageName.Console, "\uEAE8")
    {
        _backendService = backendService;
        _settingsService = settingsService;
        _commonModel = commonModel;
        _logger = logger;
        _backendService.Outputted += AddConsoleLine;
        _backendService.StartBackend(Arguments);
        FilterOptions.CollectionChanged += (_, _) => OnPropertyChanged(nameof(ConsoleLines));
    }

    private string Arguments => Environment.GetCommandLineArgs().Length > 1
        ? string.Join(' ', Environment.GetCommandLineArgs()[1..].Select(arg => arg.Contains(' ') ? $"\"{arg}\"" : arg))
        : _settingsService.Settings.Advanced.BackendLaunchArgs;

    public string ConsoleLines
    {
        get
        {
            // ConcurrentQueue 枚举线程安全，无需加锁
            var filteredLines = _consoleLines.Where(line =>
            {
                // 1. 检查是否匹配已勾选的级别（标识可能在任意位置，用 Contains）
                for (var i = 0; i < _levelPrefixes.Length; i++)
                    // 勾选了该级别，且日志行包含对应标识 → 保留
                    if (FilterOptions[i] && line.Contains(_levelPrefixes[i]))
                        return true;
                // 2. 保留无任何级别标识的日志（无匹配级别时默认保留）
                var hasAnyLevelPrefix = _levelPrefixes.Any(line.Contains);
                return !hasAnyLevelPrefix;
            });
            return string.Join('\n', filteredLines);
        }
    }

    private void AddConsoleLine(string line)
    {
        // 添加新行到队列末尾
        _consoleLines.Enqueue(line.Trim());
        // 超出最大行数时，移除最前面的旧行
        while (_consoleLines.Count > MaxConsoleLines)
            _consoleLines.TryDequeue(out _);
        // 触发UI更新
        OnPropertyChanged(nameof(ConsoleLines));
    }

    private void HandleMessage(string message)
    {
        _ = _backendService.SendInputAsync(message);
    }

    private void HandleCommand(string line)
    {
        var parts = line.Split(' ', 2);
        var command = parts[0].ToLower();
        // var args = parts.Length > 1 ? parts[1] : string.Empty;
        switch (command)
        {
            case "connect":
                AddConsoleLine("未来版本支持WebSocket连接命令");
                break;
            case "disconnect":
                AddConsoleLine("未连接到任何WebSocket服务器");
                break;
            default:
                AddConsoleLine($"未知命令: {command}");
                break;
        }
    }

    public void HandleInput(string input)
    {
        if (input.StartsWith('/'))
            HandleCommand(input[1..]);
        else
            HandleMessage(input);
    }

    [RelayCommand]
    private async Task RestartConsole()
    {
        _consoleLines.Clear();
        await _backendService.RestartBackendAsync(_settingsService.Settings.Advanced.BackendLaunchArgs);
    }

    [RelayCommand]
    private void StopConsole()
    {
        _backendService.StopBackend();
    }

    [RelayCommand]
    private async Task ExportLogsAsync()
    {
        if (TopLevelObject is null || IsExporting) return;

        // 1. 弹出保存路径选择器（含确认/取消），默认文件名 logs_YYYYMMDD_HHMMSS.zip
        var saveFile = await TopLevelObject.StorageProvider.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            Title = "导出日志",
            SuggestedFileName = $"logs_{DateTime.Now:yyyyMMdd_HHmmss}",
            DefaultExtension = "zip",
            FileTypeChoices = [new FilePickerFileType("ZIP 压缩包") { Patterns = ["*.zip"] }],
            ShowOverwritePrompt = true
        });
        if (saveFile is null) return; // 用户取消
        var targetPath = saveFile.Path.LocalPath;

        // 2. 收集日志并打包（后台线程执行，避免阻塞UI）
        IsExporting = true;
        _commonModel.ShowInfoToast("正在导出日志", "正在收集日志文件并打包，请稍候...");
        try
        {
            var (consoleLines, frontendFiles, backendFiles) = await Task.Run(() => ExportLogsCore(targetPath));
            _logger.LogInformation("Log export completed: {TargetPath} (console {Console} lines, frontend {Frontend} files, backend {Backend} files)",
                targetPath, consoleLines, frontendFiles, backendFiles);
            _commonModel.ShowSuccessToast("日志导出成功",
                $"已保存至：{targetPath}");
        }
        catch (Exception e)
        {
            _logger.LogError(e, "日志导出失败: {TargetPath}", targetPath);
            _commonModel.ShowErrorToast("日志导出失败", $"发生错误：{e.Message}\n请检查目标路径是否可写后重试");
        }
        finally
        {
            IsExporting = false;
        }
    }

    /// <summary>
    /// 收集前端/后端/控制台日志，生成清单并压缩为ZIP
    /// </summary>
    /// <returns>(控制台行数, 前端文件数, 后端文件数)</returns>
    private (int ConsoleLines, int FrontendFiles, int BackendFiles) ExportLogsCore(string targetZipPath)
    {
        var stagingDir = Path.Combine(DataPath.TempDir, "log_export", DateTime.Now.ToString("yyyyMMdd_HHmmssfff"));
        try
        {
            Directory.CreateDirectory(stagingDir);

            // 1. 控制台日志（本页面捕获的后端实时输出）
            var lines = _consoleLines.ToArray();
            File.WriteAllLines(Path.Combine(stagingDir, "console.log"), lines, Encoding.UTF8);

            // 2. 前端日志文件（Serilog 按天滚动，包含错误日志与操作日志）
            var frontendCount = CopyLogFiles(DataPath.FrontendLogsDir, Path.Combine(stagingDir, "frontend"));

            // 3. 后端日志文件
            var backendCount = CopyLogFiles(DataPath.BackendLogsDir, Path.Combine(stagingDir, "backend"));

            // 4. 导出清单（JSON）
            var manifest = new
            {
                exported_at = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
                app_version = AppSettings.Version,
                counts = new { console_lines = lines.Length, frontend_files = frontendCount, backend_files = backendCount }
            };
            File.WriteAllText(Path.Combine(stagingDir, "manifest.json"),
                JsonSerializer.Serialize(manifest, new JsonSerializerOptions { WriteIndented = true }));

            // 5. 压缩为ZIP
            if (File.Exists(targetZipPath)) File.Delete(targetZipPath);
            ZipFile.CreateFromDirectory(stagingDir, targetZipPath, CompressionLevel.Optimal, false);

            return (lines.Length, frontendCount, backendCount);
        }
        finally
        {
            // 清理临时目录，失败不影响导出结果
            try
            {
                if (Directory.Exists(stagingDir)) Directory.Delete(stagingDir, true);
            }
            catch (Exception e)
            {
                _logger.LogWarning(e, "Failed to clean up log export staging directory: {StagingDir}", stagingDir);
            }
        }
    }

    /// <summary>
    /// 递归复制目录下的所有文件到目标目录（保留相对目录结构）
    /// </summary>
    /// <returns>复制的文件数量</returns>
    private static int CopyLogFiles(string sourceDir, string destDir)
    {
        if (!Directory.Exists(sourceDir)) return 0;
        var count = 0;
        foreach (var file in Directory.EnumerateFiles(sourceDir, "*", SearchOption.AllDirectories))
        {
            var relativePath = Path.GetRelativePath(sourceDir, file);
            var destPath = Path.Combine(destDir, relativePath);
            Directory.CreateDirectory(Path.GetDirectoryName(destPath)!);
            File.Copy(file, destPath, true);
            count++;
        }
        return count;
    }
}
using System;
using System.IO;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Controls.Notifications;
using Avalonia.Media;
using Markdown.Avalonia;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SRAFrontend.utilities;
using SukiUI.Controls;
using SukiUI.MessageBox;
using SukiUI.Toasts;

namespace SRAFrontend.ViewModels;

public class CommonModel(
    SettingsService settingsService,
    CacheService cacheService,
    UpdateService updateService,
    PythonService pythonService,
    ILogger<CommonModel> logger,
    ISukiToastManager toastManager)
{
    // 常量定义（避免魔法值）
    private const string PythonDownloadTitle = "正在下载 Python 3.12...";
    private const string PipInstallTitle = "正在安装 pip...";
    private const string RequirementsInstallTitle = "正在安装 Python 依赖包...";
    private const int ToastDisplayDuration = 5; // Toast 显示时长（秒）

    public async Task CheckForUpdatesAsync()
    {
        var cdk = settingsService.Settings.MirrorChyanCdk;
        var channel = settingsService.Settings.AppChannel == 0 ? "stable" : "beta";
        
        var currentVersion = SemVerParser.Parse(Settings.Version);
        logger.LogDebug("Checking for updates: {Version}", currentVersion);
        if (currentVersion == null)
        {
            logger.LogError("Failed to parse current version: {Version}", Settings.Version);
            ShowErrorToast("检查更新失败", "当前版本号格式无效");
            return;
        }
        var response = await updateService.GetRemoteVersionAsync(currentVersion.ToString(), cdk, channel);
        if (response == null)
        {
            logger.LogError("Failed to check for updates: response is null");
            ShowErrorToast("检查更新失败", "无法获取更新信息，请检查网络连接");
            return;
        }

        // 统一解析远程版本号（容错处理）
        var remoteVersion = SemVerParser.Parse(response.Data.VersionName);
        if (remoteVersion == null)
        {
            logger.LogError("Failed to parse remote version: {VersionName}", response.Data.VersionName);
            ShowErrorToast("检查更新失败", "远程版本号格式无效");
            return;
        }

        if (!VersionHelper.NeedUpdate(currentVersion, remoteVersion, cacheService.Cache.HotfixVersion))
        {
            var installedHotfix = SemVerParser.Parse(cacheService.Cache.HotfixVersion);
            var versionText = VersionHelper.GetVersionDisplayText(currentVersion, installedHotfix);
            ShowSuccessToast("已是最新版本", versionText);
            return;
        }

        if (settingsService.Settings.EnableAutoUpdate)
        {
            ShowInfoToast("发现新版本", $"正在自动下载更新包：{response.Data.VersionName}");
            _ = HandleUpdateAsync(response, remoteVersion);
        }
        else
        {
            var autoUpgradeButton =
                SukiMessageBoxButtonsFactory.CreateButton("自动更新", SukiMessageBoxResult.Yes, "Flat Accent");
            var manualUpgradeButton =
                SukiMessageBoxButtonsFactory.CreateButton("手动更新", SukiMessageBoxResult.OK);
            var cancelButton = SukiMessageBoxButtonsFactory.CreateButton("忽略", SukiMessageBoxResult.Cancel);
            var result = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
            {
                Header = "Update Available - " + response.Data.VersionName,
                Content = new MarkdownScrollViewer
                {
                    Markdown = response.Data.ReleaseNote,
                    Width = 600,
                    Height = 400
                },
                ActionButtonsSource = [autoUpgradeButton, manualUpgradeButton, cancelButton]
            });
            switch (result)
            {
                case SukiMessageBoxResult.Yes:
                    _ = HandleUpdateAsync(response, remoteVersion);
                    break;
                case SukiMessageBoxResult.OK:
                    UrlUtil.OpenUrl("https://github.com/Shasnow/StarRailAssistant/releases/latest");
                    break;
                case SukiMessageBoxResult.Cancel:
                    break;
            }
        }
    }

    private async Task HandleUpdateAsync(VersionResponse versionResponse, SemVerInfo remoteVersion)
    {
        var currentVersion = SemVerParser.Parse(Settings.Version)!;
        var isHotfix = VersionHelper.IsHotfix(currentVersion, remoteVersion);

        var (progressPanel, progressBar, sizeLabel) = BuildDownloadProgressUi();
        var toastBuilder = CreateStandardToastBuilder("正在下载...", progressPanel, NotificationType.Information);
        toastBuilder.SetDismissAfter(TimeSpan.FromMinutes(10));
        var toast = toastBuilder.Queue();
        var progressHandler = new Progress<DownloadStatus>(value =>
        {
            progressBar.Value = value.ProgressPercent;
            sizeLabel.Content = $"{value.FormattedDownloadedSize} / {value.FormattedTotalSize} {value.FormattedSpeed}";
        });
        var proxies = settingsService.Settings.Proxies;
        var downloadChannel = settingsService.Settings.DownloadChannel;
        string downloadFilePath;
        try
        {
            downloadFilePath = isHotfix
                ? await updateService.DownloadHotfixAsync(versionResponse, progressHandler)
                : await updateService.DownloadUpdateAsync(versionResponse, downloadChannel, progressHandler,
                    proxies);
            toastManager.Dismiss(toast);
        }
        catch (Exception e)
        {
            logger.LogError(e, "Error downloading update");
            toastManager.Dismiss(toast);
            ShowErrorToast("下载更新失败", $"发生错误：{e.Message}");
            return;
        }

        ShowSuccessToast("下载完成", "更新包将在3秒后解压");
        await Task.Delay(3000);
        if (isHotfix)
        {
            logger.LogDebug("Extracting hotfix: {Source} → {Destination}", downloadFilePath, PathString.SourceCodeDir);
            ZipUtil.UnzipExternal(downloadFilePath, PathString.SourceCodeDir);

            // 保存热修复版本（直接用已解析的 Version，避免重复转换）
            cacheService.Cache.HotfixVersion = remoteVersion.ToString();
            logger.LogDebug("Hotfix applied successfully: {Version}", remoteVersion);
            ShowSuccessToast("热更新应用完成", "请重启控制台以使用最新版本");
        }
        else
        {
            logger.LogDebug("Extracting full update: {Source} → {Destination}", downloadFilePath,
                Environment.CurrentDirectory);
            ZipUtil.UnzipExternal(downloadFilePath, Environment.CurrentDirectory);
            ShowSuccessToast("更新准备完成", "应用将退出，请手动重启以完成更新");
            Environment.Exit(0);
        }
    }

    /// <summary>
    ///     检查并修复 Python 环境（核心入口）
    /// </summary>
    public async Task CheckAndFixPythonEnvironmentAsync()
    {
        try
        {
            await Task.Delay(500);
            logger.LogInformation("Starting Python environment check...");
            var pythonEnvStatus = pythonService.CheckPythonEnvironment();
            logger.LogInformation("Python EnvStatus: {Status}", pythonEnvStatus);

            // 环境正常，直接返回
            if (pythonEnvStatus == PythonEnvStatus.AllSet)
            {
                logger.LogInformation("Python environment is all set.");
                ShowSuccessToast("Python 环境正常", "无需任何操作");
                return;
            }

            // 显示修复确认弹窗
            var userAgreed = await ShowFixConfirmationDialog(pythonEnvStatus);
            if (!userAgreed)
            {
                logger.LogInformation("User canceled Python environment fix.");
                ShowWarningToast("环境修复取消", "Python 环境存在问题，可能影响部分功能使用");
                return;
            }

            // 执行修复流程（带重试机制）
            var fixSuccess = await ExecuteFixFlowAsync(pythonEnvStatus);
            if (fixSuccess)
                ShowSuccessToast("Python 环境修复完成", "所有依赖已就绪，可正常使用相关功能");
            else
                ShowErrorToast("Python 环境修复失败", "部分步骤执行失败，请查看日志或手动修复");
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Python Environment check and fix failed unexpectedly");
            ShowErrorToast("环境处理失败", $"发生未预期错误：{ex.Message}\n请重启应用重试");
        }
    }

    #region 弹窗与 Toast 封装（代码复用）

    /// <summary>
    ///     显示修复确认弹窗
    /// </summary>
    private async Task<bool> ShowFixConfirmationDialog(PythonEnvStatus status)
    {
        var statusDescription = GetStatusDescription(status);
        var fixButton = SukiMessageBoxButtonsFactory.CreateButton("立即修复", SukiMessageBoxResult.Yes, "Flat Accent");
        var cancelButton = SukiMessageBoxButtonsFactory.CreateButton("取消", SukiMessageBoxResult.Cancel);

        var result = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = "Python 环境检测到问题",
            Content = new TextBlock
            {
                Text = $"Python 环境存在以下问题：\n{statusDescription}\n\n是否立即修复？",
                TextWrapping = TextWrapping.Wrap
            },
            ActionButtonsSource = [fixButton, cancelButton],
            Width = 400 // 固定弹窗宽度，避免文本过长导致变形
        });

        return result is SukiMessageBoxResult.Yes;
    }

    /// <summary>
    ///     显示成功 Toast
    /// </summary>
    private void ShowSuccessToast(string title, string content)
    {
        CreateStandardToastBuilder(title, content, NotificationType.Success).Queue();
    }

    /// <summary>
    ///     显示警告 Toast
    /// </summary>
    private void ShowWarningToast(string title, string content)
    {
        CreateStandardToastBuilder(title, content, NotificationType.Warning).Queue();
    }

    /// <summary>
    ///     显示错误 Toast
    /// </summary>
    private void ShowErrorToast(string title, string content)
    {
        CreateStandardToastBuilder(title, content, NotificationType.Error).Queue();
    }

    /// <summary>
    ///     显示信息 Toast
    /// </summary>
    private void ShowInfoToast(string title, string content)
    {
        CreateStandardToastBuilder(title, content, NotificationType.Information).Queue();
    }

    /// <summary>
    ///     创建统一样式的 Toast（代码复用）
    /// </summary>
    private SukiToastBuilder CreateStandardToastBuilder(string title, object content, NotificationType type)
    {
        return toastManager.CreateToast()
            .OfType(type)
            .WithTitle(title)
            .WithContent(content)
            .Dismiss().After(TimeSpan.FromSeconds(ToastDisplayDuration))
            .Dismiss().ByClicking();
    }

    /// <summary>
    ///     获取环境状态的友好描述（避免用户看到枚举值）
    /// </summary>
    private string GetStatusDescription(PythonEnvStatus status)
    {
        return status switch
        {
            PythonEnvStatus.PythonNotInstalled => "未安装 Python 3.12 环境",
            PythonEnvStatus.PythonVersionMismatch => "Python 版本不匹配（需 3.12.x 版本）",
            PythonEnvStatus.PipNotInstalled => "未安装 pip 包管理工具",
            PythonEnvStatus.RequirementsNotInstalled => "缺少必要的 Python 依赖包",
            PythonEnvStatus.AllSet => "环境正常",
            _ => $"未知错误（错误码：{status}）"
        };
    }

    #endregion

    #region 修复流程核心逻辑（带重试与错误处理）

    /// <summary>
    ///     执行修复流程（按状态分步处理，支持重试）
    /// </summary>
    private async Task<bool> ExecuteFixFlowAsync(PythonEnvStatus status)
    {
        try
        {
            // 按状态执行对应修复步骤，前一步失败则终止流程
            switch (status)
            {
                case PythonEnvStatus.PythonNotInstalled or PythonEnvStatus.PythonVersionMismatch:
                    if (!await FixPythonWithRetryAsync()) return false;
                    // 穿透到下一个 case，继续修复 pip 和依赖
                    goto case PythonEnvStatus.PipNotInstalled;

                case PythonEnvStatus.PipNotInstalled:
                    if (!await FixPipWithRetryAsync()) return false;
                    // 穿透到下一个 case，继续修复依赖
                    goto case PythonEnvStatus.RequirementsNotInstalled;

                case PythonEnvStatus.RequirementsNotInstalled:
                    return await FixRequirementsWithRetryAsync();

                default:
                    logger.LogWarning("Unknown Status：{Status}", status);
                    return false;
            }
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "ExecuteFixFlowAsync failed unexpectedly");
            return false;
        }
    }

    /// <summary>
    ///     修复 Python（带重试机制）
    /// </summary>
    private async Task<bool> FixPythonWithRetryAsync(int maxRetries = 2)
    {
        for (var retry = 0; retry < maxRetries; retry++)
            try
            {
                logger.LogInformation("Starting Python fix (Attempt {Retry}/{MaxRetries})", retry + 1, maxRetries);

                // 1. 构建进度 UI
                var (progressPanel, progressBar, sizeLabel) = BuildDownloadProgressUi();
                var toastBuilder =
                    CreateStandardToastBuilder(PythonDownloadTitle, progressPanel, NotificationType.Information);
                toastBuilder.SetDismissAfter(TimeSpan.FromMinutes(10)); // 延长超时，避免下载时间过长被自动关闭
                var toast = toastBuilder.Queue();

                // 2. 下载 Python
                var md5Sum = settingsService.Settings.PythonMd5;
                var pythonZipUrl = settingsService.Settings.PythonDownloadPath;
                var progressHandler = new Progress<DownloadStatus>(value =>
                {
                    progressBar.Value = value.ProgressPercent;
                    sizeLabel.Content =
                        $"{value.FormattedDownloadedSize} / {value.FormattedTotalSize} | {value.FormattedSpeed}";
                });

                var (tempZipPath, errorMessage) =
                    await pythonService.DownloadPythonAsync(pythonZipUrl, md5Sum, progressHandler);
                toastManager.Dismiss(toast);

                // 3. 检查下载结果
                if (string.IsNullOrEmpty(tempZipPath))
                {
                    logger.LogError("Python Download Error：{ErrorMessage}", errorMessage);
                    if (retry < maxRetries - 1)
                    {
                        ShowWarningToast("下载失败", $"第 {retry + 1} 次下载失败，{errorMessage}\n将在 3 秒后重试...");
                        await Task.Delay(3000);
                        continue;
                    }

                    ShowErrorToast("Python 下载失败", $"{errorMessage}\n建议检查网络连接或手动下载");
                    return false;
                }

                // 4. 解压与初始化
                ShowSuccessToast("Python 下载完成", "正在解压并配置 Python 环境...");
                if (!await UnzipPythonAsync(tempZipPath)) return false;

                pythonService.EnableSiteModule();
                logger.LogInformation("Python Fix Successful");
                return true;
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Python Fix Attempt {Retry} Failed", retry + 1);
                if (retry < maxRetries - 1)
                {
                    ShowWarningToast("修复失败", $"第 {retry + 1} 次修复失败，{ex.Message}\n将在 3 秒后重试...");
                    await Task.Delay(3000);
                    continue;
                }

                ShowErrorToast("Python 修复失败", ex.Message);
                return false;
            }
            finally
            {
                // 清理临时文件（无论成功失败）
                CleanupPythonTempFiles();
            }

        return false;
    }

    /// <summary>
    ///     修复 pip（带重试机制）
    /// </summary>
    private async Task<bool> FixPipWithRetryAsync(int maxRetries = 2)
    {
        for (var retry = 0; retry < maxRetries; retry++)
            try
            {
                logger.LogInformation("Starting pip fix (Attempt {Retry}/{MaxRetries})", retry + 1, maxRetries);

                // 1. 构建进度 UI
                var (progressPanel, progressBar, sizeLabel) = BuildDownloadProgressUi();
                var toastBuilder =
                    CreateStandardToastBuilder(PipInstallTitle, progressPanel, NotificationType.Information);
                toastBuilder.SetDismissAfter(TimeSpan.FromMinutes(10)); // 延长超时，避免安装时间过长被自动关闭
                var toast = toastBuilder.Queue();

                // 2. 安装 pip
                var progressHandler = new Progress<DownloadStatus>(value =>
                {
                    progressBar.Value = value.ProgressPercent;
                    sizeLabel.Content =
                        $"{value.FormattedDownloadedSize} / {value.FormattedTotalSize} | {value.FormattedSpeed}";
                });

                var installSuccess = await pythonService.InstallPipAsync(progressHandler);
                toastManager.Dismiss(toast);

                if (!installSuccess)
                {
                    logger.LogError("pip Installation Failed (Attempt {Retry})", retry + 1);
                    if (retry < maxRetries - 1)
                    {
                        ShowWarningToast("pip 安装失败", $"第 {retry + 1} 次安装失败\n将在 3 秒后重试...");
                        await Task.Delay(3000);
                        continue;
                    }

                    ShowErrorToast("pip 安装失败", "请手动执行 python -m ensurepip 安装");
                    return false;
                }

                // 3. 后续配置
                ShowSuccessToast("pip 安装完成", "正在配置 pip 环境...");
                await pythonService.SetupPipAsync();

                // 二次校验 pip 是否安装成功
                if (!pythonService.CheckPipInstalled())
                {
                    logger.LogError("pip Configuration Failed After Installation");
                    if (retry < maxRetries - 1)
                    {
                        ShowWarningToast("pip 配置失败", "安装成功但配置失败，将重试...");
                        await Task.Delay(3000);
                        continue;
                    }

                    ShowErrorToast("pip 配置失败", "pip 已安装但无法使用，请检查 Python 环境变量");
                    return false;
                }

                logger.LogInformation("pip Fix Successful");
                return true;
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "pip Fix Attempt {Retry} Failed", retry + 1);
                if (retry < maxRetries - 1)
                {
                    ShowWarningToast("pip 修复失败", $"第 {retry + 1} 次修复失败，{ex.Message}\n将在 3 秒后重试...");
                    await Task.Delay(3000);
                    continue;
                }

                ShowErrorToast("pip 修复失败", ex.Message);
                return false;
            }

        return false;
    }

    /// <summary>
    ///     修复依赖包（带重试机制）
    /// </summary>
    private async Task<bool> FixRequirementsWithRetryAsync(int maxRetries = 2)
    {
        for (var retry = 0; retry < maxRetries; retry++)
            try
            {
                logger.LogInformation("Starting requirements fix (Attempt {Retry}/{MaxRetries})", retry + 1,
                    maxRetries);

                // 1. 构建进度 UI
                var logLabel = new Label { Content = "正在连接 PyPI 源..." };
                var toastBuilder =
                    CreateStandardToastBuilder(RequirementsInstallTitle, logLabel, NotificationType.Information);
                toastBuilder.SetDismissAfter(TimeSpan.FromMinutes(10)); // 延长超时，避免安装时间过长被自动关闭
                var toast = toastBuilder.Queue();

                // 2. 安装依赖
                var progressHandler = new Progress<string>(log => { logLabel.Content = log; });

                var installSuccess = await pythonService.InstallRequirementsAsync(progressHandler);
                toastManager.Dismiss(toast);

                if (!installSuccess)
                {
                    logger.LogError("Requirements Installation Failed (Attempt {Retry})", retry + 1);
                    if (retry < maxRetries - 1)
                    {
                        ShowWarningToast("依赖包安装失败", $"第 {retry + 1} 次安装失败\n将在 3 秒后重试...");
                        await Task.Delay(3000);
                        continue;
                    }

                    ShowErrorToast("依赖包安装失败", "请手动执行 pip install -r requirements.txt 安装");
                    return false;
                }

                logger.LogInformation("Requirements Fix Successful");
                return true;
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Requirements Fix Attempt {Retry} Failed", retry + 1);
                if (retry < maxRetries - 1)
                {
                    ShowWarningToast("依赖包修复失败", $"第 {retry + 1} 次修复失败，{ex.Message}\n将在 3 秒后重试...");
                    await Task.Delay(3000);
                    continue;
                }

                ShowErrorToast("依赖包修复失败", ex.Message);
                return false;
            }

        return false;
    }

    #endregion

    #region 辅助方法（UI 构建、文件清理等）

    /// <summary>
    ///     构建下载进度 UI（代码复用）
    /// </summary>
    private (StackPanel ProgressPanel, ProgressBar ProgressBar, Label SizeLabel) BuildDownloadProgressUi()
    {
        var progressBar = new ProgressBar { Value = 0, ShowProgressText = true };
        var sizeLabel = new Label { Content = "连接中..." };
        var progressPanel = new StackPanel { Children = { sizeLabel, progressBar } };
        return (progressPanel, progressBar, sizeLabel);
    }

    /// <summary>
    ///     异步解压 Python 压缩包（增加异常处理）
    /// </summary>
    private async Task<bool> UnzipPythonAsync(string zipPath)
    {
        try
        {
            // 异步解压（避免阻塞 UI）
            await Task.Run(() =>
            {
                ZipUtil.Unzip(zipPath, PathString.PythonDir);
            });

            // 校验解压结果（是否存在 python.exe）
            var pythonExePath = Path.Combine(PathString.PythonDir, "python.exe");
            if (File.Exists(pythonExePath)) return true;
            logger.LogError("Python Unzip Failed: python.exe not found after extraction");
            ShowErrorToast("解压失败", "压缩包解压不完整，未找到 Python 可执行文件");
            return false;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Python Unzip Failed with Exception");
            ShowErrorToast("解压失败", $"解压过程出错：{ex.Message}");
            return false;
        }
    }

    /// <summary>
    ///     清理 Python 临时文件（如下载的 zip 包）
    /// </summary>
    private void CleanupPythonTempFiles()
    {
        try
        {
            var tempZipPath = Path.Combine(Path.GetTempPath(), "python-3.12.10-embed-amd64.zip");
            if (!File.Exists(tempZipPath)) return;
            File.Delete(tempZipPath);
            logger.LogInformation("Successfully cleaned up Python temporary files.");
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Failed to clean up Python temporary files.");
        }
    }

    #endregion
}
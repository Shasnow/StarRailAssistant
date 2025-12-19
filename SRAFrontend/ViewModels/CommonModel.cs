using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Controls.Notifications;
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
    SraService sraService,
    ILogger<CommonModel> logger,
    ISukiToastManager toastManager)
{
    // 常量定义（避免魔法值）
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
                SukiMessageBoxButtonsFactory.CreateButton("自动更新", SukiMessageBoxResult.Yes, "Flat");
            var manualUpgradeButton =
                SukiMessageBoxButtonsFactory.CreateButton("手动更新", SukiMessageBoxResult.OK, "Flat Accent");
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

    public async Task CheckDesktopShortcut(bool forceCheck = false)
    {
        if (cacheService.Cache.NoNotifyForShortcut && !forceCheck) return;
        if (File.Exists(PathString.DesktopShortcutPath)) return;

        var createShortcutButton =
            SukiMessageBoxButtonsFactory.CreateButton("创建快捷方式", SukiMessageBoxResult.Yes, "Flat");
        var cancelButton = SukiMessageBoxButtonsFactory.CreateButton("取消", SukiMessageBoxResult.Cancel);
        var doNotAskButton =
            SukiMessageBoxButtonsFactory.CreateButton("不再询问", SukiMessageBoxResult.No, "Flat Warning");
        var result = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = "创建桌面快捷方式",
            Content = "检测到桌面快捷方式不存在，是否现在创建？",
            ActionButtonsSource = [createShortcutButton, doNotAskButton, cancelButton]
        });
        switch (result)
        {
            case SukiMessageBoxResult.No:
                cacheService.Cache.NoNotifyForShortcut = true;
                break;
            case SukiMessageBoxResult.Yes:
                if (CreateWindowsShortcut(PathString.DesktopShortcutPath, PathString.SraExePath))
                    ShowSuccessToast("快捷方式创建成功", "已在桌面创建 SRA 快捷方式");
                else
                    ShowErrorToast("快捷方式创建失败", "查看日志以获取更多信息");
                break;
        }
    }

    public async Task CleanupOldExeAsync()
    {
        if (File.Exists(PathString.SraOldExePath))
        {
            logger.LogDebug("Cleaning up old executable file: SRA_old.exe");
            await Task.Run(() => File.Delete(PathString.SraOldExePath));
        }
    }

    public void OpenFolderInExplorer(string folderPath)
    {
        try
        {
            if (!Directory.Exists(folderPath))
            {
                logger.LogWarning("Folder does not exist: {FolderPath}", folderPath);
                ShowErrorToast("打开文件夹失败", "指定的文件夹不存在");
                return;
            }

            logger.LogInformation("Opening folder: {FolderPath}", folderPath);
            Process.Start(new ProcessStartInfo
            {
                FileName = folderPath,
                UseShellExecute = true,
                Verb = "open"
            });
        }
        catch (Exception e)
        {
            logger.LogError(e, "Error opening folder: {FolderPath}", folderPath);
            ShowErrorToast("打开文件夹失败", $"发生错误：{e.Message}");
        }
    }

    private async Task HandleUpdateAsync(VersionResponse versionResponse, SemVerInfo remoteVersion)
    {
        // var currentVersion = SemVerParser.Parse(Settings.Version)!;
        // var isHotfix = VersionHelper.IsHotfix(currentVersion, remoteVersion);
        var isHotfix = false; // 这是以后可能会用到的妙妙小工具
        var (progressPanel, progressBar, sizeLabel) = BuildDownloadProgressUi();
        var toastBuilder = CreateStandardToastBuilder("正在下载...", progressPanel, NotificationType.Information);
        var downloadToast = toastBuilder.Queue();
        // 禁用自动关闭
        downloadToast.CanDismissByClicking = false;
        downloadToast.CanDismissByTime = false;
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
            toastManager.Dismiss(downloadToast);
        }
        catch (Exception e)
        {
            logger.LogError(e, "Error downloading update");
            toastManager.Dismiss(downloadToast);
            ShowErrorToast("下载更新失败", $"发生错误：{e.Message}");
            return;
        }

        ShowSuccessToast("下载完成", "更新包将在3秒后解压");
        await Task.Delay(3000);
        sraService.StopSraProcess();
        if (isHotfix)
        {
            logger.LogDebug("Extracting hotfix: {Source} -> {Destination}", downloadFilePath, PathString.SourceCodeDir);
            ZipUtil.UnzipExternal(downloadFilePath, PathString.SourceCodeDir);
            // 保存热修复版本（直接用已解析的 Version，避免重复转换）
            cacheService.Cache.HotfixVersion = remoteVersion.ToString();
            logger.LogDebug("Hotfix applied successfully: {Version}", remoteVersion);
            ShowSuccessToast("热更新应用完成", "请重启控制台以使用最新版本");
        }
        else
        {
            logger.LogDebug("Extracting full update: {Source} -> {Destination}", downloadFilePath,
                Environment.CurrentDirectory);
            var unzipToast = ShowInfoToast("正在解压更新", "请稍候...");
            unzipToast.CanDismissByClicking = false;
            unzipToast.CanDismissByTime = false;
            try
            {
                // 重命名当前可执行文件（以防更新过程中被占用）
                File.Move(PathString.SraExePath, PathString.SraOldExePath);
                // 解压更新包
                await Task.Run(() => ZipUtil.Unzip(downloadFilePath, Environment.CurrentDirectory));
                toastManager.Dismiss(unzipToast);
            }
            catch (Exception e)
            {
                toastManager.Dismiss(unzipToast);
                logger.LogError(e, "Error extracting update");
                ShowErrorToast("更新解压失败", $"发生错误，应用程序将退出以重新解压：{e.Message}");
                await Task.Delay(5000);
                ZipUtil.UnzipExternal(downloadFilePath, Environment.CurrentDirectory);
                Environment.Exit(0);
                return;
            }

            ShowSuccessToast("更新准备完成", "重启应用程序以应用最新版本");
            var restartNowButton =
                SukiMessageBoxButtonsFactory.CreateButton("立即重启", SukiMessageBoxResult.Yes, "Flat");
            var restartLaterButton =
                SukiMessageBoxButtonsFactory.CreateButton("稍后", SukiMessageBoxResult.Cancel);
            var result = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
            {
                Header = "更新已准备就绪",
                Content = "是否现在重启应用以应用最新版本？",
                ActionButtonsSource = [restartNowButton, restartLaterButton]
            });
            if (result is SukiMessageBoxResult.Yes) RestartApplication();
        }
    }

    private void RestartApplication()
    {
        var exePath = PathString.SraExePath;
        try
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = exePath,
                WorkingDirectory = Environment.CurrentDirectory,
                UseShellExecute = true
            });
            Environment.Exit(0);
        }
        catch (Exception e)
        {
            logger.LogError(e, "Error restarting application");
            ShowErrorToast("重启失败", $"发生错误：{e.Message}");
        }
    }

    private bool CreateWindowsShortcut(string shortcutPath, string appExePath)
    {
        logger.LogDebug("Creating Windows shortcut: {ShortcutPath} -> {AppExePath}", shortcutPath, appExePath);
        // 使用 VBScript 创建快捷方式
        var vbsScript = $"""

                                 Set WshShell = WScript.CreateObject("WScript.Shell")
                                 Set shortcut = WshShell.CreateShortcut("{shortcutPath}")
                                 shortcut.TargetPath = "{appExePath}"
                                 shortcut.WorkingDirectory = "{Path.GetDirectoryName(appExePath)}"
                                 shortcut.Save
                             
                         """;
        var vbsPath = Path.Combine(Path.GetTempPath(), "create_shortcut.vbs");
        try
        {
            File.WriteAllText(vbsPath, vbsScript);

            // 执行 VBScript
            using var process = new Process();
            process.StartInfo = new ProcessStartInfo
            {
                FileName = "cscript.exe",
                Arguments = $"/nologo \"{vbsPath}\"",
                UseShellExecute = false,
                CreateNoWindow = true
            };
            process.Start();
            process.WaitForExit();
            File.Delete(vbsPath); // 删除临时脚本

            return File.Exists(shortcutPath);
        }
        catch (Exception e)
        {
            logger.LogError(e, "Error creating shortcut");
            return false;
        }
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
    private ISukiToast ShowInfoToast(string title, string content)
    {
        return CreateStandardToastBuilder(title, content, NotificationType.Information).Queue();
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
    ///     构建下载进度 UI（代码复用）
    /// </summary>
    private (StackPanel ProgressPanel, ProgressBar ProgressBar, Label SizeLabel) BuildDownloadProgressUi()
    {
        var progressBar = new ProgressBar { Value = 0, ShowProgressText = true };
        var sizeLabel = new Label { Content = "连接中..." };
        var progressPanel = new StackPanel { Children = { sizeLabel, progressBar } };
        return (progressPanel, progressBar, sizeLabel);
    }
}
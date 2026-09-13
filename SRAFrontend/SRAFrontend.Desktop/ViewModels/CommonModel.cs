using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Controls.Notifications;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Desktop.Controls;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SRAFrontend.Utils;
using SukiUI.Controls;
using SukiUI.MessageBox;
using SukiUI.Toasts;

namespace SRAFrontend.Desktop.ViewModels;

public class CommonModel(
    SettingsService settingsService,
    CacheService cacheService,
    UpdateService updateService,
    IBackendService backendService,
    AnnService annService,
    ILogger<CommonModel> logger,
    ISukiToastManager toastManager)
{
    // 常量定义（避免魔法值）
    private const int ToastDisplayDuration = 5; // Toast 显示时长（秒）

    public void ShowAnnouncementBoard()
    {
        SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = "公告",
            Content = new AnnBoardViewModel
            {
                Announcements = annService.CachedAnnouncements?.Announcements
            }
        });
    }

    public async Task CheckAnnouncementAsync()
    {
        if (await annService.HasNewAnnouncementsAsync(cacheService.Cache.LastViewAnnouncementId))
        {
            ShowAnnouncementBoard();
            cacheService.Cache.LastViewAnnouncementId = annService.LatestAnnouncementId;
        }
    }

    public async Task CheckForUpdatesAsync()
    {
        var cdk = settingsService.Settings.Update.MirrorChyanCdk;
        var channel = settingsService.Settings.Update.UpdateChannel == 0 ? "stable" : "beta";

        var currentVersion = SemVerParser.Parse(AppSettings.Version);
        logger.LogDebug("Checking for updates: {Version}", currentVersion);
        if (currentVersion == null)
        {
            logger.LogError("Failed to parse current version: {Version}", AppSettings.Version);
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

        if (settingsService.Settings.Update.IsAutoUpdate)
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
            var releaseNoteViewer = new ThemedMarkdownScrollViewer
            {
                Markdown = response.Data.ReleaseNote
            };
            
            var result = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
            {
                Header = "Update Available - " + response.Data.VersionName,
                Content = releaseNoteViewer,
                ActionButtonsSource = [autoUpgradeButton, manualUpgradeButton, cancelButton]
            }, new SukiMessageBoxOptions
            {
                CanResize = true
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
        if (File.Exists(DataPath.DesktopShortcutPath))
        {
            if (forceCheck) ShowSuccessToast("快捷方式已存在", "快捷方式已存在于桌面");
            return;
        }

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
                if (CreateDesktopShortcut(DataPath.DesktopShortcutPath, DataPath.SraExecutablePath))
                    ShowSuccessToast("快捷方式创建成功", "已在桌面创建 SRA 快捷方式");
                else
                    ShowErrorToast("快捷方式创建失败", "查看日志以获取更多信息");
                break;
        }
    }

    public async Task CleanupOldExeAsync()
    {
        
        if (File.Exists(DataPath.SraOldExecutablePath))
        {
            logger.LogDebug("Cleaning up old executable file: SRA_old.exe");
            await Task.Run(() =>
            {
                try
                {
                    File.Delete(DataPath.SraOldExecutablePath);
                }
                catch (Exception e)
                {
                    logger.LogError(e, "Failed to delete old executable file: SRA_old.exe");
                    ShowErrorToast("清理旧文件失败", $"无法删除旧可执行文件：{e.Message}");
                }
            });
        }
    }

    public void OpenFolderInExplorer(string path)
    {
        try
        {
            if (File.Exists(path))
            {
                logger.LogInformation("Selecting file in explorer: {FilePath}", path);
                if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = "explorer.exe",
                        Arguments = $"/select,\"{path}\"",
                        UseShellExecute = true
                    });
                }
                else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
                {
                    Process.Start("open", $"-R \"{path}\"");
                }
                else if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
                {
                    // nautilus 支持 --select 参数，其他文件管理器回退到打开所在文件夹
                    var dir = Path.GetDirectoryName(path);
                    Process.Start("xdg-open", dir ?? path);
                }
            }
            else if (Directory.Exists(path))
            {
                logger.LogInformation("Opening folder: {FolderPath}", path);
                if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = path,
                        UseShellExecute = true,
                        Verb = "open"
                    });
                }
                else
                {
                    Process.Start("xdg-open", path);
                }
            }
            else
            {
                logger.LogWarning("Path does not exist: {Path}", path);
                ShowErrorToast("打开失败", "指定的路径不存在");
            }
        }
        catch (Exception e)
        {
            logger.LogError(e, "Error opening path: {Path}", path);
            ShowErrorToast("打开失败", $"发生错误：{e.Message}");
        }
    }

    private async Task HandleUpdateAsync(VersionResponse versionResponse, SemVerInfo remoteVersion)
    {
        // var currentVersion = SemVerParser.Parse(Settings.Version)!;
        // var isHotfix = VersionHelper.IsHotfix(currentVersion, remoteVersion);
        var isHotfix = false; // 这是以后可能会用到的妙妙小工具
        var (progressPanel, progressLabel, progressBar, cts) = BuildDownloadProgressUi();
        
        var toastBuilder = CreateStandardToastBuilder("正在下载...", progressPanel, NotificationType.Information);
        var downloadToast = toastBuilder.Queue();
        // 禁用自动关闭
        downloadToast.CanDismissByClicking = false;
        downloadToast.CanDismissByTime = false;
        var progressHandler = new Progress<DownloadStatus>(value =>
        {
            progressBar.Value = value.ProgressPercent;
            progressLabel.Content = $"{value.FormattedDownloadedSize} / {value.FormattedTotalSize} {value.FormattedSpeed}";
        });
        var downloadChannel = settingsService.Settings.Update.DownloadChannel;
        var downloadDir = settingsService.Settings.Update.DownloadPath;
        string downloadFilePath;
        try
        {
            downloadFilePath = isHotfix
                ? await updateService.DownloadHotfixAsync(versionResponse, progressHandler, cts.Token)
                : await updateService.DownloadUpdateAsync(versionResponse, downloadChannel, progressHandler,
                    cts.Token, downloadDir);
        }
        catch (OperationCanceledException)
        {
            logger.LogInformation("Update download canceled by user");
            ShowWarningToast("下载已取消", "您已取消更新包的下载");
            return;
        }
        catch (Exception e)
        {
            logger.LogError(e, "Error downloading update");
            ShowErrorToast("下载更新失败", $"发生错误：{e.Message}");
            return;
        }
        finally
        {
            toastManager.Dismiss(downloadToast);
        }

        ShowSuccessToast("下载完成", "更新包已就绪");
        if (!settingsService.Settings.Update.IsAutoUpdate)
        {
            var extractNowButton =
                SukiMessageBoxButtonsFactory.CreateButton("立即解压", SukiMessageBoxResult.Yes, "Flat Accent");
            var extractLaterButton =
                SukiMessageBoxButtonsFactory.CreateButton("稍后", SukiMessageBoxResult.Cancel);
            var extractResult = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
            {
                Header = "更新包已下载完成",
                Content = "解压过程将短暂停止后端服务，是否现在开始解压？",
                ActionButtonsSource = [extractNowButton, extractLaterButton]
            });
            if (extractResult is not SukiMessageBoxResult.Yes)
            {
                ShowInfoToast("已推迟解压", "可稍后重新检查更新以继续");
                return;
            }
        }
        else
        {
            ShowInfoToast("即将开始解压", "更新包将在3秒后解压");
            await Task.Delay(3000);
        }
        backendService.StopBackend();
        if (isHotfix)
        {
            logger.LogDebug("Extracting hotfix: {Source} -> {Destination}", downloadFilePath, DataPath.SourceCodeDir);
            ZipUtil.UnzipExternal(downloadFilePath, DataPath.SourceCodeDir);
            // 保存热修复版本（直接用已解析的 Version，避免重复转换）
            cacheService.Cache.HotfixVersion = remoteVersion.ToString();
            logger.LogDebug("Hotfix applied successfully: {Version}", remoteVersion);
            ShowSuccessToast("热更新应用完成", "请重启控制台以使用最新版本");
        }
        else
        {
            logger.LogDebug("Extracting full update: {Source} -> {Destination}", downloadFilePath,
                Environment.CurrentDirectory);
            if (!await TryExtractFullPackageAsync(downloadFilePath)) return;

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

    /// <summary>
    ///     重新安装最新版本：用户确认后下载最新版本完整安装包（复用缓存并严格执行 SHA256 校验，
    ///     不做版本高低比较），解压后自动重启应用。与正常更新共用下载进度、解压与错误处理流程。
    /// </summary>
    public async Task ReinstallLatestAsync()
    {
        var confirmButton =
            SukiMessageBoxButtonsFactory.CreateButton("确认", SukiMessageBoxResult.Yes, "Flat Accent");
        var cancelButton = SukiMessageBoxButtonsFactory.CreateButton("取消", SukiMessageBoxResult.Cancel);
        var confirmResult = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = "重新安装最新版本",
            Content = "此操作将重新下载并安装最新版本安装包，以修复可能存在的问题。是否继续？",
            ActionButtonsSource = [cancelButton, confirmButton]
        });
        if (confirmResult is not SukiMessageBoxResult.Yes) return;

        var cdk = settingsService.Settings.Update.MirrorChyanCdk;
        var updateChannel = settingsService.Settings.Update.UpdateChannel == 0 ? "stable" : "beta";
        var downloadChannel = settingsService.Settings.Update.DownloadChannel;

        var (progressPanel, progressLabel, progressBar, cts) = BuildDownloadProgressUi();
        var downloadToast =
            CreateStandardToastBuilder("正在下载最新版本安装包...", progressPanel, NotificationType.Information).Queue();
        downloadToast.CanDismissByClicking = false;
        downloadToast.CanDismissByTime = false;
        var progressHandler = new Progress<DownloadStatus>(value =>
        {
            progressBar.Value = value.ProgressPercent;
            progressLabel.Content = $"{value.FormattedDownloadedSize} / {value.FormattedTotalSize} {value.FormattedSpeed}";
        });

        string downloadFilePath;
        string latestVersion;
        try
        {
            var (versionResponse, packagePath) = await updateService.ReinstallLatestVersionAsync(
                downloadChannel, progressHandler, cdk, updateChannel, cts.Token,
                settingsService.Settings.Update.DownloadPath);
            downloadFilePath = packagePath;
            latestVersion = versionResponse.Data.VersionName;
        }
        catch (OperationCanceledException)
        {
            logger.LogInformation("Reinstall download canceled by user");
            ShowWarningToast("操作已取消", "您已取消安装包的下载");
            return;
        }
        catch (HttpRequestException e)
        {
            logger.LogError(e, "Network error while downloading latest package");
            ShowErrorToast("重新安装失败",
                "网络错误：无法下载最新版本安装包，请检查网络连接，或在更新设置中切换下载渠道后重试。");
            return;
        }
        catch (Exception e)
        {
            logger.LogError(e, "Error reinstalling latest version");
            ShowErrorToast("重新安装失败", e.Message);
            return;
        }
        finally
        {
            toastManager.Dismiss(downloadToast);
        }

        ShowSuccessToast("下载完成", $"版本 {latestVersion} 安装包 SHA256 校验通过，即将开始安装");
        await Task.Delay(1500);

        backendService.StopBackend();
        if (!await TryExtractFullPackageAsync(downloadFilePath)) return;

        ShowInfoToast("安装完成", "应用将在 3 秒后自动重启");
        await Task.Delay(3000);
        RestartApplication();
    }

    /// <summary>
    ///     解压完整安装包到当前目录：重命名当前 exe 防占用，再做 MD5 增量覆盖。
    ///     解压失败时弹窗提供"手动解压（打开目录）"或"退出程序后外部解压"两种处理。
    /// </summary>
    /// <returns>true 表示解压成功；false 表示失败且用户已选择手动处理或退出程序。</returns>
    private async Task<bool> TryExtractFullPackageAsync(string downloadFilePath)
    {
        var unzipToast = ShowInfoToast("正在解压更新", "请稍候...");
        unzipToast.CanDismissByClicking = false;
        unzipToast.CanDismissByTime = false;
        try
        {
            // 重命名当前可执行文件（以防更新过程中被占用），覆盖上次更新残留的旧文件
            File.Move(DataPath.SraExecutablePath, DataPath.SraOldExecutablePath, true);
            // 解压更新包（后台线程执行，避免阻塞 UI）
            await Task.Run(() => ZipUtil.Unzip(downloadFilePath, Environment.CurrentDirectory));
            toastManager.Dismiss(unzipToast);
            return true;
        }
        catch (Exception e)
        {
            toastManager.Dismiss(unzipToast);
            logger.LogError(e, "Error extracting update package");
            var manualExtractButton =
                SukiMessageBoxButtonsFactory.CreateButton("手动解压", SukiMessageBoxResult.Yes, "Flat");
            var exitButton =
                SukiMessageBoxButtonsFactory.CreateButton("退出程序", SukiMessageBoxResult.OK, "Flat");
            var extractResult = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
            {
                Header = "更新解压失败",
                Content = $"自动解压失败：{e.Message}\n\n需要退出程序完成解压（退出后请等待5~10秒），或手动完成解压",
                ActionButtonsSource = [manualExtractButton, exitButton]
            });
            if (extractResult is SukiMessageBoxResult.Yes)
            {
                // 打开压缩包所在文件夹并选中压缩包
                OpenFolderInExplorer(downloadFilePath);
            }
            else
            {
                // 使用外部解压工具重试
                ZipUtil.UnzipExternal(downloadFilePath, Environment.CurrentDirectory);
                Environment.Exit(0);
            }
            return false;
        }
    }

    private void RestartApplication()
    {
        var exePath = DataPath.SraExecutablePath;
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

    private bool CreateDesktopShortcut(string shortcutPath, string appExePath)
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
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

        if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
        {
            logger.LogDebug("Creating Linux desktop entry: {ShortcutPath} -> {AppExePath}", shortcutPath, appExePath);
            var desktopEntry = $"""
                                 [Desktop Entry]
                                 Version=1.0
                                 Type=Application
                                 Name=SRA
                                 Exec={appExePath}
                                 Icon={Path.Combine(Path.GetDirectoryName(appExePath) ?? "", "sra_icon.png")}
                                 Terminal=false
                                 Categories=Utility;
                                 """;
            try
            {
                File.WriteAllText(shortcutPath, desktopEntry);
                return File.Exists(shortcutPath);
            } catch (Exception e)
            {
                logger.LogError(e, "Error creating shortcut");
                return false;
            }
        }
        return false;
    }

    /// <summary>
    ///     显示成功 Toast
    /// </summary>
    public void ShowSuccessToast(string title, string content)
    {
        CreateStandardToastBuilder(title, content, NotificationType.Success).Queue();
    }

    /// <summary>
    ///     显示警告 Toast
    /// </summary>
    public void ShowWarningToast(string title, string content)
    {
        CreateStandardToastBuilder(title, content, NotificationType.Warning).Queue();
    }

    /// <summary>
    ///     显示错误 Toast
    /// </summary>
    public void ShowErrorToast(string title, string content)
    {
        CreateStandardToastBuilder(title, content, NotificationType.Error).Queue();
    }

    /// <summary>
    ///     显示信息 Toast
    /// </summary>
    public ISukiToast ShowInfoToast(string title, string content)
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
    private (StackPanel ProgressPanel, Label ProgressLabel, ProgressBar progressBar, CancellationTokenSource Cts) BuildDownloadProgressUi()
    {
        var progressLabel = new Label { Content = "连接中..." };
        var progressBar = new ProgressBar { Value = 0, ShowProgressText = true };
        var cancelButton = new Button { Content = "取消下载" };
        var cts = new CancellationTokenSource();
        cancelButton.Click += (_, _) =>
        {
            if (cts.IsCancellationRequested) return;
            cts.Cancel();
            progressLabel.Content = "正在取消...";
            cancelButton.IsEnabled = false;
        };
        var progressPanel = new StackPanel { Children = { progressLabel, progressBar, cancelButton } };
        return (progressPanel, progressLabel, progressBar, cts);
    }
}

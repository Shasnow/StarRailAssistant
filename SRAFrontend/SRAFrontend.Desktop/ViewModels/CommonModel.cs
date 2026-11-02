using System;
using System.Collections.Generic;
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
using SRAFrontend.Localization;

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
            Header = Resources.AnnouncementsText,
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
            ShowErrorToast(Resources.UpdateCheckFailedError, Resources.CurrentVersionInvalidError);
            return;
        }

        var response = await updateService.GetRemoteVersionAsync(currentVersion.ToString(), cdk, channel);
        if (response == null)
        {
            logger.LogError("Failed to check for updates: response is null");
            ShowErrorToast(Resources.UpdateCheckFailedError, Resources.UpdateInfoNetworkError);
            return;
        }

        // 统一解析远程版本号（容错处理）
        var remoteVersion = SemVerParser.Parse(response.Data.VersionName);
        if (remoteVersion == null)
        {
            logger.LogError("Failed to parse remote version: {VersionName}", response.Data.VersionName);
            ShowErrorToast(Resources.UpdateCheckFailedError, Resources.RemoteVersionInvalidError);
            return;
        }

        if (!VersionHelper.NeedUpdate(currentVersion, remoteVersion, cacheService.Cache.HotfixVersion))
        {
            var installedHotfix = SemVerParser.Parse(cacheService.Cache.HotfixVersion);
            var versionText = VersionHelper.GetVersionDisplayText(currentVersion, installedHotfix);
            ShowSuccessToast(Resources.UpToDateMessage, versionText);
            return;
        }

        if (settingsService.Settings.Update.IsAutoUpdate)
        {
            ShowInfoToast(Resources.NewVersionAvailableMessage, string.Format(Resources.Culture, Resources.UpdateAutoDownloadMessage, response.Data.VersionName));
            _ = HandleUpdateAsync(response, remoteVersion, channel);
        }
        else
        {
            var autoUpgradeButton =
                SukiMessageBoxButtonsFactory.CreateButton(Resources.AutoUpdateText, SukiMessageBoxResult.Yes, "Flat");
            var manualUpgradeButton =
                SukiMessageBoxButtonsFactory.CreateButton(Resources.UpdateManualModeText, SukiMessageBoxResult.OK, "Flat Accent");
            var cancelButton = SukiMessageBoxButtonsFactory.CreateButton(Resources.IgnoreText, SukiMessageBoxResult.Cancel);
            var releaseNoteViewer = new ThemedMarkdownScrollViewer
            {
                Markdown = response.Data.ReleaseNote,
                Width = 800,
                Height = 600
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
                    _ = HandleUpdateAsync(response, remoteVersion, channel);
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
            if (forceCheck) ShowSuccessToast(Resources.ShortcutExistsMessage, Resources.DesktopShortcutExistsMessage);
            return;
        }

        var createShortcutButton =
            SukiMessageBoxButtonsFactory.CreateButton(Resources.CreateShortcutActionText, SukiMessageBoxResult.Yes, "Flat");
        var cancelButton = SukiMessageBoxButtonsFactory.CreateButton(Resources.CancelText, SukiMessageBoxResult.Cancel);
        var doNotAskButton =
            SukiMessageBoxButtonsFactory.CreateButton(Resources.DoNotAskAgainText, SukiMessageBoxResult.No, "Flat Warning");
        var result = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = Resources.CreateShortcutText,
            Content = Resources.DesktopShortcutMissingMessage,
            ActionButtonsSource = [createShortcutButton, doNotAskButton, cancelButton]
        });
        switch (result)
        {
            case SukiMessageBoxResult.No:
                cacheService.Cache.NoNotifyForShortcut = true;
                break;
            case SukiMessageBoxResult.Yes:
                if (CreateDesktopShortcut(DataPath.DesktopShortcutPath, DataPath.SraExecutablePath))
                    ShowSuccessToast(Resources.ShortcutCreatedMessage, Resources.SraShortcutCreatedMessage);
                else
                    ShowErrorToast(Resources.ShortcutCreateFailedError, Resources.CheckLogsHint);
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
                    ShowErrorToast(Resources.OldFilesCleanupFailedError, string.Format(Resources.Culture, Resources.OldExecutableDeleteFailedError, e.Message));
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
                ShowErrorToast(Resources.OpenFailedError, Resources.PathNotExistError);
            }
        }
        catch (Exception e)
        {
            logger.LogError(e, "Error opening path: {Path}", path);
            ShowErrorToast(Resources.OpenFailedError, string.Format(Resources.Culture, Resources.UnexpectedErrorMessage, e.Message));
        }
    }

    private async Task HandleUpdateAsync(VersionResponse versionResponse, SemVerInfo remoteVersion,
        string updateChannel)
    {
        // var currentVersion = SemVerParser.Parse(Settings.Version)!;
        // var isHotfix = VersionHelper.IsHotfix(currentVersion, remoteVersion);
        var isHotfix = false; // 这是以后可能会用到的妙妙小工具
        var (progressPanel, progressLabel, progressBar, cts) = BuildDownloadProgressUi();
        
        var toastBuilder = CreateStandardToastBuilder(Resources.DownloadingMessage, progressPanel, NotificationType.Information);
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
                : await updateService.DownloadUpdateAsync(versionResponse, downloadChannel, updateChannel,
                    progressHandler, cts.Token, downloadDir);
        }
        catch (OperationCanceledException)
        {
            logger.LogInformation("Update download canceled by user");
            ShowWarningToast(Resources.DownloadCanceledMessage, Resources.UpdateDownloadCanceledMessage);
            return;
        }
        catch (Exception e)
        {
            logger.LogError(e, "Error downloading update");
            ShowErrorToast(Resources.UpdateDownloadFailedError, string.Format(Resources.Culture, Resources.UnexpectedErrorMessage, e.Message));
            return;
        }
        finally
        {
            toastManager.Dismiss(downloadToast);
        }

        ShowSuccessToast(Resources.DownloadCompleteMessage, Resources.UpdatePackageReadyMessage);
        if (!settingsService.Settings.Update.IsAutoUpdate)
        {
            var extractNowButton =
                SukiMessageBoxButtonsFactory.CreateButton(Resources.ExtractNowText, SukiMessageBoxResult.Yes, "Flat Accent");
            var extractLaterButton =
                SukiMessageBoxButtonsFactory.CreateButton(Resources.LaterText, SukiMessageBoxResult.Cancel);
            var extractResult = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
            {
                Header = Resources.UpdatePackageDownloadedMessage,
                Content = Resources.ExtractionConfirmMessage,
                ActionButtonsSource = [extractNowButton, extractLaterButton]
            });
            if (extractResult is not SukiMessageBoxResult.Yes)
            {
                ShowInfoToast(Resources.ExtractionPostponedMessage, Resources.UpdateCheckLaterHint);
                return;
            }
        }
        else
        {
            ShowInfoToast(Resources.ExtractionStartingMessage, Resources.ExtractionCountdownMessage);
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
            ShowSuccessToast(Resources.HotUpdateAppliedMessage, Resources.RestartConsoleHint);
        }
        else
        {
            logger.LogDebug("Extracting full update: {Source} -> {Destination}", downloadFilePath,
                Environment.CurrentDirectory);
            if (!await TryExtractFullPackageAsync(downloadFilePath)) return;

            ShowSuccessToast(Resources.UpdatePreparationCompleteMessage, Resources.RestartToApplyHint);
            var restartNowButton =
                SukiMessageBoxButtonsFactory.CreateButton(Resources.RestartNowText, SukiMessageBoxResult.Yes, "Flat");
            var restartLaterButton =
                SukiMessageBoxButtonsFactory.CreateButton(Resources.LaterText, SukiMessageBoxResult.Cancel);
            var result = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
            {
                Header = Resources.UpdateReadyMessage,
                Content = Resources.RestartConfirmMessage,
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
            SukiMessageBoxButtonsFactory.CreateButton(Resources.EnsureText, SukiMessageBoxResult.Yes, "Flat Accent");
        var cancelButton = SukiMessageBoxButtonsFactory.CreateButton(Resources.CancelText, SukiMessageBoxResult.Cancel);
        var confirmResult = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = Resources.ReInstallText,
            Content = Resources.ReinstallConfirmMessage,
            ActionButtonsSource = [cancelButton, confirmButton]
        });
        if (confirmResult is not SukiMessageBoxResult.Yes) return;

        var cdk = settingsService.Settings.Update.MirrorChyanCdk;
        var updateChannel = settingsService.Settings.Update.UpdateChannel == 0 ? "stable" : "beta";
        var downloadChannel = settingsService.Settings.Update.DownloadChannel;

        var (progressPanel, progressLabel, progressBar, cts) = BuildDownloadProgressUi();
        var downloadToast =
            CreateStandardToastBuilder(Resources.InstallerDownloadingMessage, progressPanel, NotificationType.Information).Queue();
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
                downloadChannel, progressHandler, updateChannel, cdk,
                cts.Token, settingsService.Settings.Update.DownloadPath);
            downloadFilePath = packagePath;
            latestVersion = versionResponse.Data.VersionName;
        }
        catch (OperationCanceledException)
        {
            logger.LogInformation("Reinstall download canceled by user");
            ShowWarningToast(Resources.OperationCanceledMessage, Resources.InstallerDownloadCanceledMessage);
            return;
        }
        catch (HttpRequestException e)
        {
            logger.LogError(e, "Network error while downloading latest package");
            ShowErrorToast(Resources.ReinstallFailedError,
                Resources.InstallerDownloadNetworkError);
            return;
        }
        catch (Exception e)
        {
            logger.LogError(e, "Error reinstalling latest version");
            ShowErrorToast(Resources.ReinstallFailedError, e.Message);
            return;
        }
        finally
        {
            toastManager.Dismiss(downloadToast);
        }

        ShowSuccessToast(Resources.DownloadCompleteMessage, string.Format(Resources.Culture, Resources.InstallerSha256PassedMessage, latestVersion));
        await Task.Delay(1500);

        backendService.StopBackend();
        if (!await TryExtractFullPackageAsync(downloadFilePath)) return;

        ShowInfoToast(Resources.InstallationCompleteMessage, Resources.AutoRestartCountdownMessage);
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
        var unzipToast = ShowInfoToast(Resources.UpdateExtractingMessage, Resources.PleaseWaitMessage);
        unzipToast.CanDismissByClicking = false;
        unzipToast.CanDismissByTime = false;
        try
        {
            // 记录更新前的文件清单：增量解压只覆盖不删除，解压完成后据此回收旧版本残留
            ZipUtil.TryLoadManifest(Environment.CurrentDirectory, out var previousManifest);
            // 重命名当前可执行文件（以防更新过程中被占用），覆盖上次更新残留的旧文件
            File.Move(DataPath.SraExecutablePath, DataPath.SraOldExecutablePath, true);
            // 解压更新包（后台线程执行，避免阻塞 UI）
            await Task.Run(() => ZipUtil.Unzip(downloadFilePath, Environment.CurrentDirectory));
            toastManager.Dismiss(unzipToast);
            await CleanupObsoleteFilesAsync(previousManifest);
            return true;
        }
        catch (Exception e)
        {
            toastManager.Dismiss(unzipToast);
            logger.LogError(e, "Error extracting update package");
            var manualExtractButton =
                SukiMessageBoxButtonsFactory.CreateButton(Resources.ExtractManuallyText, SukiMessageBoxResult.Yes, "Flat");
            var exitButton =
                SukiMessageBoxButtonsFactory.CreateButton(Resources.ExitProgramText, SukiMessageBoxResult.OK, "Flat");
            var extractResult = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
            {
                Header = Resources.UpdateExtractFailedError,
                Content = string.Format(Resources.Culture, Resources.AutoExtractFailedError, e.Message),
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

    /// <summary>
    ///     回收旧版本残留：应用内更新只做 MD5 增量覆盖、不删除旧文件，更新成功后按新旧清单差集
    ///     删除被移除的依赖、旧运行时等文件（日志与用户自建文件不在清单中，不会被删除）。
    ///     清单缺失（如安装包直接安装）或删除失败（文件被占用）时静默跳过，不影响更新结果。
    /// </summary>
    private async Task CleanupObsoleteFilesAsync(IReadOnlyDictionary<string, string> previousManifest)
    {
        if (previousManifest.Count == 0) return;
        try
        {
            var (deletedCount, freedBytes, failedFiles) = await Task.Run(() =>
                ZipUtil.RemoveObsoleteFiles(Environment.CurrentDirectory, previousManifest));
            logger.LogInformation(
                "Cleaned up {DeletedCount} obsolete files, freed {FreedSize}, {FailedCount} failed",
                deletedCount, ZipUtil.FormatFileSize(freedBytes), failedFiles.Count);
            if (deletedCount == 0) return;
            ShowInfoToast(Resources.ObsoleteFilesCleanedText,
                string.Format(Resources.Culture, Resources.ObsoleteFilesDeletedMessage, deletedCount, ZipUtil.FormatFileSize(freedBytes)));
        }
        catch (Exception e)
        {
            // 清理属于附加操作，失败不应让更新流程失败
            logger.LogWarning(e, "Failed to clean up obsolete files after update");
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
            ShowErrorToast(Resources.RestartFailedError, string.Format(Resources.Culture, Resources.UnexpectedErrorMessage, e.Message));
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
        var progressLabel = new Label { Content = Resources.ConnectingMessage };
        var progressBar = new ProgressBar { Value = 0, ShowProgressText = true };
        var cancelButton = new Button { Content = Resources.CancelDownloadText };
        var cts = new CancellationTokenSource();
        cancelButton.Click += (_, _) =>
        {
            if (cts.IsCancellationRequested) return;
            cts.Cancel();
            progressLabel.Content = Resources.CancelingMessage;
            cancelButton.IsEnabled = false;
        };
        var progressPanel = new StackPanel { Children = { progressLabel, progressBar, cancelButton } };
        return (progressPanel, progressLabel, progressBar, cts);
    }
}

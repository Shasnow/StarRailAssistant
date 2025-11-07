using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using Avalonia.Collections;
using Avalonia.Controls;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Markdown.Avalonia;
using SRAFrontend.Controls;
using SRAFrontend.Localization;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SRAFrontend.utilities;
using SukiUI;
using SukiUI.Controls;
using SukiUI.MessageBox;
using SukiUI.Toasts;
using Version = SRAFrontend.utilities.Version;

namespace SRAFrontend.ViewModels;

public partial class MainWindowViewModel : ViewModelBase
{
    private readonly AnnouncementService _announcementService;
    private readonly SettingsService _settingsService;
    private readonly UpdateService _updateService;

    [ObservableProperty] private string _lightModeText =
        SukiTheme.GetInstance().ActiveBaseTheme.ToString() == "Light" ? "\uE472" : "\uE330";

    [ObservableProperty] private bool _titleBarVisible = true;

    public MainWindowViewModel(IEnumerable<PageViewModel> pages, ISukiToastManager toastManager,
        AnnouncementService announcementService, SettingsService settingsService, UpdateService updateService)
    {
        _announcementService = announcementService;
        Pages = new AvaloniaList<PageViewModel>(pages);
        ToastManager = toastManager;
        _settingsService = settingsService;
        _updateService = updateService;
        _ = CheckForUpdates();
    }

    public ISukiToastManager ToastManager { get; init; }

    public string Greeting { get; } = Resources.GreetingText;

    public IAvaloniaReadOnlyList<PageViewModel> Pages { get; }

    public void SwitchLightMode()
    {
        SukiTheme.GetInstance().SwitchBaseTheme();
        LightModeText = SukiTheme.GetInstance().ActiveBaseTheme.ToString() == "Light" ? "\uE472" : "\uE330";
    }

    [RelayCommand]
    private static void OpenUrl(string url)
    {
        UrlUtil.OpenUrl(url);
    }

    [RelayCommand]
    private void ShowAnnouncementBoard()
    {
        SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = "公告",
            Content = new AnnouncementBoardViewModel(_announcementService)
        });
    }

    private async Task CheckForUpdates()
    {
        var cdk = _settingsService.Settings.MirrorChyanCdk;
        var channel = _settingsService.Settings.AppChannel == 0 ? "stable" : "beta";
        var currentVersion = new Version(Settings.Version);
        var response = await _updateService.CheckForUpdatesAsync(currentVersion.ToString(), cdk, channel);
        if (response == null)
        {
            ToastManager.CreateToast()
                .WithTitle("Update Check Failed")
                .WithContent("Could not connect to the update server.")
                .Dismiss().After(TimeSpan.FromSeconds(3))
                .Dismiss().ByClicking()
                .Queue();
            return;
        }

        if (currentVersion >= new Version(response.Data.VersionName))
            return;
        if (_settingsService.Settings.EnableAutoUpdate)
        {
            ToastManager.CreateToast()
                .WithTitle("Update Available")
                .WithContent(
                    $"A new version {response.Data.VersionName} is available and will be downloaded automatically.")
                .Dismiss().After(TimeSpan.FromSeconds(3))
                .Dismiss().ByClicking()
                .Queue();
            _ = DownloadUpdateAsync(response);
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
                    Markdown = response.Data.ReleaseNote
                },
                ActionButtonsSource = [autoUpgradeButton, manualUpgradeButton, cancelButton]
            });
            switch (result)
            {
                case SukiMessageBoxResult.Yes:
                    _ = DownloadUpdateAsync(response);
                    break;
                case SukiMessageBoxResult.OK:
                    UrlUtil.OpenUrl("https://github.com/Shasnow/StarRailAssistant/releases/latest");
                    break;
                case SukiMessageBoxResult.Cancel:
                    break;
            }
        }
    }

    private async Task DownloadUpdateAsync(VersionResponse versionResponse)
    {
        var progressBar = new ProgressBar { Value = 0, ShowProgressText = true };
        var sizeLabel = new Label { Content = "Connecting..." };
        var progress = new StackPanel { Children = { sizeLabel, progressBar } };
        var toast = ToastManager.CreateToast()
            .WithTitle("Updating...")
            .WithContent(progress)
            .Queue();
        var progressHandler = new Progress<DownloadStatus>(value =>
        {
            progressBar.Value = value.ProgressPercent;
            sizeLabel.Content = $"{value.FormattedDownloadedSize} / {value.FormattedTotalSize} {value.FormattedSpeed}";
        });
        var proxies = _settingsService.Settings.Proxies;
        var downloadChannel = _settingsService.Settings.DownloadChannel;
        string result;
        try
        {
            result = await _updateService.DownloadUpdateAsync(versionResponse, downloadChannel, progressHandler,
                proxies);
        }
        catch (Exception e)
        {
            Console.WriteLine(e);
            return;
        }

        ToastManager.Dismiss(toast);
        ToastManager.CreateToast()
            .WithTitle("Download Complete")
            .WithContent("Update package will be unzip within 3 seconds.")
            .Dismiss().After(TimeSpan.FromSeconds(3))
            .Dismiss().ByClicking()
            .Queue();
        await Task.Delay(3000);
        UnzipUtil.Unzip(result, Path.GetDirectoryName(result)!);
    }
}
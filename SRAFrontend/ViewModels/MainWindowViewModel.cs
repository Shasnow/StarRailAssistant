using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Localization;
using SRAFrontend.Utils;
using SukiUI;
using SukiUI.Toasts;

namespace SRAFrontend.ViewModels;

public partial class MainWindowViewModel(
    IEnumerable<PageViewModel> pages,
    CommonModel commonModel,
    ISukiToastManager toastManager)
    : ViewModelBase
{
    private static readonly List<string> GreetingsZh =
    [
        "欢迎使用 SRA",
        "坐和放宽",
        "not 'Sequence Read Archive'",
        "启动器启动启动器",
        "-1073741819",
        "飞荧扑火，向死而生",
        "跨越寰宇终抵黯淡星外",
        "立志成为崩铁糕手"
    ];

    private static readonly List<string> GreetingsEn =
    [
        "Welcome to SRA",
        "Sit back and relax",
        "not 'Sequence Read Archive'",
        "Launcher launching launcher",
        "-1073741819"
    ];

    [ObservableProperty] private string _lightModeText =
        SukiTheme.GetInstance().ActiveBaseTheme.ToString() == "Light" ? "\uE472" : "\uE330";

    public static string GreetingMessage
    {
        get
        {
            var rand = new Random();
            return Resources.Culture.Name == "zh-CN"
                ? GreetingsZh[rand.Next(GreetingsZh.Count)]
                : GreetingsEn[rand.Next(GreetingsEn.Count)];
        }
    }

    public ISukiToastManager ToastManager { get; init; } = toastManager;

    public IAvaloniaReadOnlyList<PageViewModel> Pages { get; } = new AvaloniaList<PageViewModel>(pages);

    /// <summary>
    ///     异步初始化方法，在应用启动时调用 (MainWindow.xaml.cs)
    /// </summary>
    public async Task InitializeAsync()
    {
        await commonModel.CleanupOldExeAsync();
        await commonModel.CheckForUpdatesAsync();
        await commonModel.CheckDesktopShortcut();
        await commonModel.CheckAnnouncementAsync();
    }

    [RelayCommand]
    private void SwitchLightMode()
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
        commonModel.ShowAnnouncementBoard();
    }
}
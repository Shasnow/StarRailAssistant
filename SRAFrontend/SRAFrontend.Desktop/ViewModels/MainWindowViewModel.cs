using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using Avalonia.Collections;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Desktop.Controls;
using SRAFrontend.Desktop.Models;
using SRAFrontend.Desktop.Services;
using SRAFrontend.Localization;
using SRAFrontend.Services;
using SRAFrontend.Utils;
using SukiUI;
using SukiUI.Controls;
using SukiUI.MessageBox;
using SukiUI.Toasts;

namespace SRAFrontend.Desktop.ViewModels;

public partial class MainWindowViewModel : ViewModelBase
{
    private readonly ActivityService _activityService;
    private readonly CommonModel _commonModel;
    private readonly CommandPaletteService _commandPaletteService;

    [ObservableProperty] private string _lightModeText =
        SukiTheme.GetInstance().ActiveBaseTheme.ToString() == "Light" ? "\uE472" : "\uE330";

    /// <summary>当前侧边栏页面，命令面板通过切换它在页面间跳转。</summary>
    [ObservableProperty] private PageViewModel? _selectedPage;

    [ObservableProperty] private bool _isPaletteOpen;
    [ObservableProperty]
    public partial string PaletteQuery { get; set; } = "";

    [ObservableProperty] private PaletteCommand? _paletteSelected;

    public MainWindowViewModel(
        IEnumerable<PageViewModel> pages,
        CommonModel commonModel,
        ActivityService activityService,
        AppService appService,
        ISukiToastManager toastManager,
        CommandPaletteService commandPaletteService)
    {
        _commonModel = commonModel;
        _activityService = activityService;
        _commandPaletteService = commandPaletteService;
        ToastManager = toastManager;
        GreetingMessage = appService.GetPhrase();
        Pages = new AvaloniaList<PageViewModel>(pages);
        SelectedPage = Pages[0];
        RegisterPaletteCommands();
        PaletteResults = new ObservableCollection<PaletteCommand>(
            _commandPaletteService.Commands.OrderBy(command => command.Category));
        PaletteSelected = PaletteResults.FirstOrDefault();
        // 其他视图模型可能在使用过程中补充命令，集合变化后刷新过滤结果
        _commandPaletteService.Changed += (_, _) => Dispatcher.UIThread.Post(RefreshPaletteResults);
    }

    public string GreetingMessage { get; }

    public ISukiToastManager ToastManager { get; }

    public IAvaloniaReadOnlyList<PageViewModel> Pages { get; }

    public ObservableCollection<PaletteCommand> PaletteResults { get; }

    public bool HasNoPaletteResults => PaletteResults.Count == 0;

    /// <summary>
    ///     异步初始化方法，在应用启动时调用 (MainWindow.xaml.cs)
    /// </summary>
    public async Task InitializeAsync()
    {
        await _commonModel.CleanupOldExeAsync();
        await _commonModel.CheckAnnouncementAsync();
        await _commonModel.CheckForUpdatesAsync();
        await _commonModel.CheckDesktopShortcut();
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
        _commonModel.ShowAnnouncementBoard();
    }

    [RelayCommand]
    private void ShowActivity()
    {
        var viewModel = new ActivityPageViewModel(_activityService);
        var view = new ActivityPageView { DataContext = viewModel };
        SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = Resources.EventCalendarText,
            Content = view
        });
    }

    private void RegisterPaletteCommands()
    {
        foreach (var page in Pages)
        {
            _commandPaletteService.Register(new PaletteCommand(page.DisplayName, $"view.toggle{page.PageId}", PaletteCategory.View)
            {
                Execute = () => SelectedPage = page
            });
        }

        _commandPaletteService.Register(new PaletteCommand(Resources.ToggleThemeTooltip, "view.toggleTheme", PaletteCategory.View)
        {
            Execute = SwitchLightMode
        });
        _commandPaletteService.Register(new PaletteCommand(Resources.AnnouncementsText, "view.announcements", PaletteCategory.View)
        {
            Execute = ShowAnnouncementBoard
        });
        _commandPaletteService.Register(new PaletteCommand(Resources.EventCalendarText, "view.events", PaletteCategory.View)
        {
            Execute = ShowActivity
        });
        _commandPaletteService.Register(new PaletteCommand(Resources.GithubToolTipText, "open.github", PaletteCategory.Link)
        {
            Execute = () => UrlUtil.OpenUrl("https://github.com/Shasnow/StarRailAssistant")
        });
        _commandPaletteService.Register(new PaletteCommand(Resources.WebsiteToolTipText, "open.website", PaletteCategory.Link)
        {
            Execute = () => UrlUtil.OpenUrl("https://starrailassistant.top")
        });
        _commandPaletteService.Register(new PaletteCommand(Resources.FaqText, "open.faq", PaletteCategory.Link)
        {
            Execute = () => UrlUtil.OpenUrl("https://starrailassistant.top/getting-started/faq/")
        });
        _commandPaletteService.Register(new PaletteCommand(Resources.SponsorText, "open.sponsor", PaletteCategory.Link)
        {
            Execute = () => UrlUtil.OpenUrl("https://starrailassistant.top/sponsor/")
        });
    }

    [RelayCommand]
    private void OpenPalette()
    {
        PaletteQuery = "";
        RefreshPaletteResults();
        IsPaletteOpen = true;
    }

    [RelayCommand]
    private void ClosePalette()
    {
        IsPaletteOpen = false;
    }

    [RelayCommand]
    private void RunSelectedPalette()
    {
        var command = PaletteSelected;
        if (command is null) return;
        ClosePalette();
        command.Execute?.Invoke();
    }

    /// <summary>命令面板中上下移动选中项，超出两端时循环。</summary>
    public void MovePaletteSelection(int delta)
    {
        if (PaletteResults.Count == 0) return;
        var index = PaletteSelected is null ? -1 : PaletteResults.IndexOf(PaletteSelected);
        index = (index + delta + PaletteResults.Count) % PaletteResults.Count;
        PaletteSelected = PaletteResults[index];
    }

    partial void OnPaletteQueryChanged(string value)
    {
        RefreshPaletteResults();
    }

    private void RefreshPaletteResults()
    {
        var query = PaletteQuery.Trim();
        var matched = _commandPaletteService.Commands.Where(command =>
                query.Length == 0 ||
                command.Title.Contains(query, StringComparison.OrdinalIgnoreCase) ||
                command.Subtitle.Contains(query, StringComparison.OrdinalIgnoreCase))
            .OrderBy(command => command.Category)
            .ToList();
        PaletteResults.Clear();
        foreach (var command in matched) PaletteResults.Add(command);
        PaletteSelected = PaletteResults.FirstOrDefault();
        OnPropertyChanged(nameof(HasNoPaletteResults));
    }
}

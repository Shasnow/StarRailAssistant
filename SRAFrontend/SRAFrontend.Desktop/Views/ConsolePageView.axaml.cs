using System;
using System.ComponentModel;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Threading;
using SRAFrontend.Desktop.ViewModels;

namespace SRAFrontend.Desktop.Views;

public partial class ConsolePageView : UserControl
{
    private const int RefreshDebounceMs = 100;

    /// <summary>视口距底部小于该像素值视为“贴底”，继续跟随最新日志</summary>
    private const double AutoFollowThreshold = 40;

    private bool _refreshScheduled;

    public ConsolePageView()
    {
        InitializeComponent();
    }

    private void OnModelOnPropertyChanged(object? _, PropertyChangedEventArgs args)
    {
        if (args.PropertyName == nameof(ConsolePageViewModel.ConsoleLines)) ScheduleConsoleRefresh();
    }

    /// <summary>防抖合并连续日志事件，避免高频输出时整页行内样式反复重建</summary>
    private void ScheduleConsoleRefresh()
    {
        if (_refreshScheduled) return;
        _refreshScheduled = true;
        Dispatcher.UIThread.Post(async () =>
        {
            await Task.Delay(RefreshDebounceMs);
            _refreshScheduled = false;
            RefreshConsole();
        });
    }

    private void RefreshConsole()
    {
        if (DataContext is ConsolePageViewModel model) ConsoleText.Inlines = model.ConsoleLines;
        // 仅在视口原本贴底时才滚动：ScrollToEnd 会触发布局，且用户回看历史时不应被强制拉回底部
        if (IsNearBottom()) ConsoleScrollViewer.ScrollToEnd();
    }

    private bool IsNearBottom()
    {
        var scroller = ConsoleScrollViewer;
        return scroller.Offset.Y + scroller.Viewport.Height >= scroller.Extent.Height - AutoFollowThreshold;
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        RefreshConsole();
        // 页面切回会重建本视图，OnLoaded 时首次布局尚未完成，ScrollToEnd 会被钳制到 0，
        // 导致后续 IsNearBottom 一直误判为“未贴底”而停止跟随；等首次布局完成后再补一次滚到底
        ConsoleScrollViewer.LayoutUpdated += ScrollToEndAfterLayout;
        if (DataContext is ConsolePageViewModel model)
        {
            model.TopLevelObject = TopLevel.GetTopLevel(this);
            model.PropertyChanged += OnModelOnPropertyChanged;
        }
    }

    private void ScrollToEndAfterLayout(object? sender, EventArgs e)
    {
        // 尚未完成测量（Viewport 为 0）时保留订阅，等下一次布局再滚
        if (ConsoleScrollViewer.Viewport.Height <= 0) return;
        ConsoleScrollViewer.LayoutUpdated -= ScrollToEndAfterLayout;
        ConsoleScrollViewer.ScrollToEnd();
    }

    protected override void OnUnloaded(RoutedEventArgs e)
    {
        base.OnUnloaded(e);
        ConsoleScrollViewer.LayoutUpdated -= ScrollToEndAfterLayout;
        if (DataContext is ConsolePageViewModel model) model.PropertyChanged -= OnModelOnPropertyChanged;
    }

    private void InputElement_OnKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
        {
            if (sender is not TextBox textBox) return;
            if (textBox.Text != null) (DataContext as ConsolePageViewModel)?.HandleInput(textBox.Text);
            textBox.Text = string.Empty;
        }
    }
}
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
    private const int RefreshDebounceMs = 80;
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
        ConsoleScrollViewer.ScrollToEnd();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        RefreshConsole();
        if (DataContext is ConsolePageViewModel model)
        {
            model.TopLevelObject = TopLevel.GetTopLevel(this);
            model.PropertyChanged += OnModelOnPropertyChanged;
        }
    }

    protected override void OnUnloaded(RoutedEventArgs e)
    {
        base.OnUnloaded(e);
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
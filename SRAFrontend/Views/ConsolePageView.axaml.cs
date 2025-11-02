using System.ComponentModel;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Threading;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Views;

public partial class ConsolePageView : UserControl
{
    public ConsolePageView()
    {
        InitializeComponent();
    }

    private void OnModelOnPropertyChanged(object? _, PropertyChangedEventArgs args)
    {
        if (args.PropertyName == nameof(ConsolePageViewModel.LogText))
        {
            Dispatcher.UIThread.Post(() =>
            {
                ConsoleScrollViewer.ScrollToEnd();
            });
        }
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        ConsoleScrollViewer.ScrollToEnd();
        if (DataContext is ConsolePageViewModel model) model.PropertyChanged += OnModelOnPropertyChanged;
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
            if (textBox.Text != null) (DataContext as ConsolePageViewModel)?.SendInput(textBox.Text);
            textBox.Text = string.Empty;
        }
    }
}
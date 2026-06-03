using Avalonia.Interactivity;
using SRAFrontend.Desktop.ViewModels;
using SukiUI.Controls;

namespace SRAFrontend.Desktop.Views;

public partial class MainWindow : SukiWindow
{
    public MainWindow()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        (DataContext as MainWindowViewModel)?.InitializeAsync();
    }
}
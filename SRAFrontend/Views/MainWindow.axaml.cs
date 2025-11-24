using Avalonia.Controls;
using Avalonia.Interactivity;
using SRAFrontend.ViewModels;
using SukiUI.Controls;

namespace SRAFrontend.Views;

public partial class MainWindow : SukiWindow
{
    public static TopLevel? TopLevelObject { get; set; }
    public MainWindow()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        (DataContext as MainWindowViewModel)?.InitializeAsync();
        TopLevelObject = this;
    }
}
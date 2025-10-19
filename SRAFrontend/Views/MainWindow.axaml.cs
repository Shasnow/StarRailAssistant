using Avalonia.Interactivity;
using SRAFrontend.ViewModels;
using SukiUI.Controls;

namespace SRAFrontend.Views;

public partial class MainWindow : SukiWindow
{
    public MainWindow()
    {
        InitializeComponent();
    }

    private void SwitchLightModeButton_OnClick(object? sender, RoutedEventArgs e)
    {
        (DataContext as MainWindowViewModel)?.SwitchLightMode();
    }
    
}
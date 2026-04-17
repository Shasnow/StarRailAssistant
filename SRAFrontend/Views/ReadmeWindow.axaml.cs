using Avalonia.Controls;
using Avalonia.Interactivity;

namespace SRAFrontend.Views;

public partial class ReadmeWindow : Window
{
    public ReadmeWindow()
    {
        InitializeComponent();
    }

    private void CloseButton_Click(object? sender, RoutedEventArgs e) => Close();
}

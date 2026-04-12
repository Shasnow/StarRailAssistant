using Avalonia.Controls;
using Avalonia.Interactivity;

namespace SRAFrontend.Views;

public partial class ScriptConfigWindow : Window
{
    public ScriptConfigWindow()
    {
        InitializeComponent();
    }

    private void CloseButton_Click(object? sender, RoutedEventArgs e) => Close();
}

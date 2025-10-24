using Avalonia.Controls;
using Avalonia.Input;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Views;

public partial class ConsolePageView : UserControl
{
    public ConsolePageView()
    {
        InitializeComponent();
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
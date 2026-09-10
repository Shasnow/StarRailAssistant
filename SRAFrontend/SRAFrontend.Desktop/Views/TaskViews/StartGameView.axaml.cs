using Avalonia.Controls;
using Avalonia.Input;
using SRAFrontend.Desktop.ViewModels;

namespace SRAFrontend.Desktop.Views.TaskViews;

public partial class StartGameView : UserControl
{
    public StartGameView()
    {
        InitializeComponent();
    }

    private void OnAccountTextBoxGotFocus(object? sender, FocusChangedEventArgs e)
    {
        if (DataContext is TaskPageViewModel viewModel)
        {
            viewModel.ToggleAccountTextFocus(true);
        }
    }

    private void OnAccountTextBoxLostFocus(object? sender, FocusChangedEventArgs e)
    {
        if (DataContext is TaskPageViewModel viewModel)
        {
            viewModel.ToggleAccountTextFocus(false);
        }
    }
}
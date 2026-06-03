using Avalonia.Controls;
using Avalonia.Interactivity;
using SRAFrontend.Desktop.ViewModels;

namespace SRAFrontend.Desktop.Views;

public partial class TaskPageView : UserControl
{
    public TaskPageView()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        if (DataContext is not TaskPageViewModel viewModel) return;
        var topLevel = TopLevel.GetTopLevel(this);
        viewModel.TopLevelObject = topLevel;
    }
}
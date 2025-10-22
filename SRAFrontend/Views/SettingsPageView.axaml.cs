using Avalonia.Controls;
using Avalonia.Interactivity;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Views;

public partial class SettingsPageView : UserControl
{
    public SettingsPageView()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        if (DataContext is not SettingsPageViewModel viewModel) return;
        var topLevel = TopLevel.GetTopLevel(this);
        viewModel.Zoom = topLevel?.RenderScaling ?? 1;
    }
}
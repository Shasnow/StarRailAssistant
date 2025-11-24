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
        base.OnLoaded(e);
        if (DataContext is not SettingsPageViewModel viewModel) return;
        var topLevel = TopLevel.GetTopLevel(this);
        viewModel.Settings.Zoom = topLevel?.RenderScaling ?? 1;
        viewModel.TopLevelObject = topLevel;
    }
}
using Avalonia.Controls;
using Avalonia.Interactivity;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Views;

public partial class SettingPageView : UserControl
{
    public SettingPageView()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        if (DataContext is not SettingPageViewModel viewModel) return;
        var topLevel = TopLevel.GetTopLevel(this);
        viewModel.Zoom = topLevel?.RenderScaling ?? 1;
    }
}
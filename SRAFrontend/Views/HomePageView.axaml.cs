using Avalonia.Controls;
using Avalonia.Interactivity;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Views;

public partial class HomePageView : UserControl
{
    public HomePageView()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        (DataContext as HomePageViewModel)?.UpdateBackgroundImageAsync();
    }
}
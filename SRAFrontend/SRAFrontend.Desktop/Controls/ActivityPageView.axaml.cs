using Avalonia.Controls;
using Avalonia.Interactivity;

namespace SRAFrontend.Desktop.Controls;

public partial class ActivityPageView : UserControl
{
    public ActivityPageView()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        (DataContext as ActivityPageViewModel)?.LoadCommand.Execute(null);
    }
}
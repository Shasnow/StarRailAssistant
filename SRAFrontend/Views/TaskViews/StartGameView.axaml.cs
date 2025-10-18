using Avalonia.Controls;
using Avalonia.Interactivity;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Views.TaskViews;

public partial class StartGameView : UserControl
{
    public StartGameView()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        if (DataContext is TaskPageViewModel { TopLevelObject: null } model)
        {
            model.TopLevelObject= TopLevel.GetTopLevel(this);
        }
    }
}
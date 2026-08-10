using Avalonia.Controls;
using Avalonia.Interactivity;
using SRAFrontend.Desktop.ViewModels;
using SRAFrontend.Utils;

namespace SRAFrontend.Desktop.Views;

public partial class ExtensionPageView : UserControl
{
    public ExtensionPageView()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        (DataContext as ExtensionPageViewModel)?.LoadExtensionsCommand.Execute(null);
    }

    private void Button_OnClick(object? sender, RoutedEventArgs e)
    {
        UrlUtil.OpenUrl("https://catcake.hoshimi.io/");
    }
}
using Avalonia.Controls;
using Avalonia.Interactivity;
using SRAFrontend.Utils;

namespace SRAFrontend.Views;

public partial class ExtensionPageView : UserControl
{
    public ExtensionPageView()
    {
        InitializeComponent();
    }

    private void Button_OnClick(object? sender, RoutedEventArgs e)
    {
        UrlUtil.OpenUrl("https://catcake.hoshimi.io/");
    }
}
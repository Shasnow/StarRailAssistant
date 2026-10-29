using System;
using Avalonia;
using Avalonia.Markup.Xaml.Styling;

namespace SRAFrontend.Desktop.Styles;

public static class RussianTypography
{
    public static void Apply(Application application, int language)
    {
        if (language != 2) return;
        application.Styles.Add(new StyleInclude(new Uri("avares://SRA/"))
        {
            Source = new Uri("avares://SRA/Styles/RussianTypography.axaml")
        });
    }
}

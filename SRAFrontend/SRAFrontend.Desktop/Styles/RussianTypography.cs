using System;
using Avalonia;
using Avalonia.Markup.Xaml.Styling;
using SRAFrontend.Models;

namespace SRAFrontend.Desktop.Styles;

public static class RussianTypography
{
    public static void Apply(Application application, UiLanguage language)
    {
        if (language != UiLanguage.Russian) return;
        application.Styles.Add(new StyleInclude(new Uri("avares://SRA/"))
        {
            Source = new Uri("avares://SRA/Styles/RussianTypography.axaml")
        });
    }
}

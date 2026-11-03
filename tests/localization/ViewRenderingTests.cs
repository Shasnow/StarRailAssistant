using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;
using Avalonia.Media.Imaging;
using Avalonia.Styling;
using Avalonia.Threading;
using Avalonia.VisualTree;
using SRAFrontend.Desktop;
using SRAFrontend.Desktop.Styles;
using SRAFrontend.Desktop.ViewModels;
using SRAFrontend.Desktop.Views;
using SRAFrontend.Desktop.Views.TaskViews;
using SRAFrontend.Localization;
using SRAFrontend.Models;
using SukiUI;
using SukiUI.Controls;
using Xunit;

namespace SRALocalizationChecks;

/// <summary>
/// 用无头 SukiUI 宿主渲染真实页面，覆盖三种语言、明暗主题与 800/1024 两档宽度。
/// 不启动 App.OnFrameworkInitializationCompleted、SettingsService、注册表、更新器或后端任务；
/// 设置/任务页面没有运行时数据上下文，扩展表单使用合成的字段。
/// </summary>
[Collection("Avalonia")]
public sealed class ViewRenderingTests(AvaloniaSession session)
{
    public static IEnumerable<object[]> Pages()
    {
        foreach (var language in new[] { UiLanguage.Chinese, UiLanguage.English, UiLanguage.Russian })
        foreach (var dark in new[] { false, true })
        foreach (var width in new[] { 800, 1024 })
        foreach (var page in new[] { "settings", "console", "currency-wars", "extensions" })
            yield return [language, dark, width, page];
    }

    [Theory]
    [MemberData(nameof(Pages))]
    public void Renders_and_keeps_text_inside_the_window(UiLanguage language, bool dark, int width, string page)
    {
        session.Run(() =>
        {
            var theme = dark ? ThemeVariant.Dark : ThemeVariant.Light;
            App.ConfigureCulture(language);
            if (language == UiLanguage.Russian)
                RussianTypography.Apply(Application.Current!, language);
            Application.Current!.RequestedThemeVariant = theme;
            SukiTheme.GetInstance().ChangeBaseTheme(theme);

            var content = page switch
            {
                "settings" => new SettingsPageView(),
                "console" => new ConsolePageView(),
                "currency-wars" => new CosmicStrife(),
                _ => ExtensionFixture()
            };
            var window = new SukiWindow
            {
                Width = width,
                Height = 700,
                Content = content,
                BackgroundAnimationEnabled = false,
                TitleBarAnimationEnabled = false
            };
            window.Show();
            Dispatcher.UIThread.RunJobs();
            window.UpdateLayout();

            Assert.True(content.Bounds.Width > 0 && content.Bounds.Height > 0, $"{page} 没有布局尺寸");
            var text = content.GetVisualDescendants().OfType<TextBlock>()
                .Where(node => !string.IsNullOrEmpty(node.Text)).ToArray();
            Assert.NotEmpty(text);

            if (language == UiLanguage.Russian)
            {
                Assert.Contains(text, node => node.Text!.Any(ch => ch is >= 'А' and <= 'я'));
                if (page == "settings")
                {
                    var label = text.FirstOrDefault(node => node.Text == Resources.RetryAfterTaskFailureText);
                    Assert.NotNull(label);
                    Assert.Equal(TextWrapping.Wrap, label.TextWrapping);
                }
                if (page == "console")
                {
                    var hint = text.SingleOrDefault(node => node.Text == Resources.LogReportHint);
                    Assert.NotNull(hint);
                    Assert.Equal(TextWrapping.Wrap, hint.TextWrapping);
                    Assert.True(hint.Bounds.Width > 0 && hint.Bounds.Right <= content.Bounds.Width,
                        "控制台说明文字超出窗口宽度");
                    foreach (var filter in text.Where(node => node.Text is "Trace" or "Debug" or "Info" or "Warn" or "Error"))
                        Assert.True(filter.TextLayout.Height <= filter.Bounds.Height + 1, "控制台过滤标签行高溢出");
                }
            }

            using var bitmap = new RenderTargetBitmap(new PixelSize(width, 700), new Vector(96, 96));
            bitmap.Render(window);
            bitmap.Save(Path.Combine(TestEnvironment.OutputDirectory,
                $"{language}-{theme.Key}-{width}-{page}.png"), PngBitmapEncoderOptions.Default);
            window.Close();
        });
    }

    [Fact]
    public void Cyrillic_glyphs_render_with_the_system_typeface()
    {
        session.Run(() =>
        {
            var typeface = new Typeface("Segoe UI").GlyphTypeface;
            foreach (var ch in "РусскийЯяЁё")
                Assert.True(typeface.CharacterToGlyphMap.TryGetGlyph(ch, out var glyph) && glyph != 0,
                    $"缺少西里尔字形 U+{(int)ch:X4}");
        });
    }

    private static Control ExtensionFixture()
    {
        var model = new ExtensionConfigDialogViewModel("CurrencyWarsPlus", null!) { IsLoading = false };
        model.Fields.Add(new StringFieldViewModel
        {
            Key = "开拓者名称",
            Label = Resources.M0053,
            Description = Resources.M0048,
            Value = "Тест"
        });
        model.Fields.Add(new IntegerFieldViewModel
        {
            Key = "运行次数",
            Label = Resources.RunCountLabelText,
            Description = Resources.M0050,
            Value = 1,
            Minimum = 1,
            Maximum = 99999
        });
        return new ExtensionConfigDialogView { DataContext = model };
    }
}

using System.Collections;
using System.Globalization;
using System.Resources;
using System.Text;
using System.Text.Json;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Headless;
using Avalonia.Markup.Xaml.Styling;
using Avalonia.Media;
using Avalonia.Media.Imaging;
using Avalonia.Styling;
using Avalonia.Threading;
using Avalonia.VisualTree;
using Microsoft.Extensions.Logging.Abstractions;
using SRAFrontend.Desktop.Styles;
using SRAFrontend.Desktop.ViewModels;
using SRAFrontend.Desktop.Views;
using SRAFrontend.Desktop.Views.TaskViews;
using SRAFrontend.Localization;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SukiUI;
using SukiUI.Controls;

internal static class Program
{
    private static int _checks;

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
        _checks++;
    }

    [STAThread]
    private static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        if (args.Length != 3)
            throw new ArgumentException("Usage: SRALocalizationChecks <repository> <output-directory> <python-3.12>");
        var root = Path.GetFullPath(args[0]);
        var output = Path.GetFullPath(args[1]);
        Directory.CreateDirectory(output);

        CheckResources(output);
        CheckPipes(root, args[2]).GetAwaiter().GetResult();
        AppBuilder.Configure<LocalizationApp>()
            .UseSkia()
            .UseHeadless(new AvaloniaHeadlessPlatformOptions { UseHeadlessDrawing = false })
            .SetupWithoutStarting();
        CheckViews(output);
        File.WriteAllText(Path.Combine(output, "result.json"), JsonSerializer.Serialize(new
        {
            passed = _checks,
            native_application_started = false,
            game_started = false,
            user_settings_accessed = false
        }, new JsonSerializerOptions { WriteIndented = true }), Encoding.UTF8);
        Console.WriteLine($"PASS: {_checks} localization / UTF-8 / headless checks");
        return 0;
    }

    private static void CheckResources(string output)
    {
        var originalCulture = CultureInfo.CurrentCulture;
        var originalDefaultCulture = CultureInfo.DefaultThreadCurrentCulture;
        try
        {
            CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo("en-US");
            CultureInfo.DefaultThreadCurrentCulture = CultureInfo.GetCultureInfo("ja-JP");
            foreach (var language in new[] { 0, 1, 2 })
            {
                UiText.ApplyCulture(language);
                Check(CultureInfo.CurrentCulture.Name == "en-US", "UI language preserves parsing culture");
                Check(CultureInfo.DefaultThreadCurrentCulture.Name == "ja-JP", "UI language preserves default parsing culture");
            }
            Check(UiText.F($"剩余 {1.5} 小时") == "Осталось: 1,5 ч.", "Russian display formatting uses UI culture");
        }
        finally
        {
            CultureInfo.CurrentCulture = originalCulture;
            CultureInfo.DefaultThreadCurrentCulture = originalDefaultCulture;
        }
        foreach (var language in new[] { 0, 1, 2 })
        {
            UiText.ApplyCulture(language);
            Check(Resources.Culture?.Name == new[] { "zh-CN", "en-US", "ru-RU" }[language], "Culture mapping");
            var settings = new AppSettings();
            settings.Display.Language = language;
            var path = Path.Combine(output, $"settings-{language}.json");
            File.WriteAllText(path, JsonSerializer.Serialize(settings), Encoding.UTF8);
            var restored = JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(path))!;
            Check(restored.Display.Language == language, "Persisted numeric language");
            // These paths are explicit fixtures, never DataPath.SettingsJson or SettingsService.Load().
        }
        UiText.ApplyCulture(2);
        Check(UiText.T("并非\n'Sequence Read Archive'").StartsWith("Это не"), "Greeting LF");
        Check(UiText.T("并非\r\n'Sequence Read Archive'").StartsWith("Это не"), "Greeting CRLF");
        Check(UiText.F($"剩余 {2} 天 {3} 小时") == "Осталось: 2 дн. 3 ч.", "Formatted arguments");
        Check(UiText.T("private-user-value") == "private-user-value", "Unknown values preserved");
        foreach (var stem in new[] { "Resources", "ExtraResources" })
        {
            var manager = new ResourceManager($"SRAFrontend.Localization.{stem}", typeof(UiText).Assembly);
            var source = manager.GetResourceSet(CultureInfo.GetCultureInfo("zh-CN"), true, true)!;
            var russian = manager.GetResourceSet(CultureInfo.GetCultureInfo("ru-RU"), true, true)!;
            foreach (DictionaryEntry item in source)
                Check(russian.GetString((string)item.Key) != null, $"Russian satellite key: {stem}.{item.Key}");
        }
        var field = new EnumFieldViewModel { Key = "难度", Label = UiText.T("难度") };
        field.SetValue(JsonSerializer.SerializeToElement(2));
        field.UpdateOptions(new[] { 0, 1, 2 }.Select(value => JsonSerializer.SerializeToElement(value)).ToArray(),
                            new[] { "最低难度", "最高难度", "当前难度" });
        Check(field.Key == "难度", "Stored alias unchanged");
        Check(field.GetValueAsJson().GetInt32() == 2, "Stored enum type/value unchanged");
        Check(field.SelectedOption?.Label == "Текущая", "Localized enum label");
        foreach (var language in new[] { 0, 1 })
        {
            UiText.ApplyCulture(language);
            Check(UiText.T("最低难度") == "最低难度", "Existing language text unchanged");
        }
    }

    private static async Task CheckPipes(string root, string python)
    {
        const string payload = "中文 Русский English ё — → {braces}";
        foreach (var codepage in new[] { "cp1251", "cp1252", "gbk" })
        {
            var oldEncoding = Environment.GetEnvironmentVariable("PYTHONIOENCODING");
            var oldUtf8 = Environment.GetEnvironmentVariable("PYTHONUTF8");
            Environment.SetEnvironmentVariable("PYTHONIOENCODING", codepage + ":strict");
            Environment.SetEnvironmentVariable("PYTHONUTF8", "0");
            var fixture = new EchoBackend
            {
                FileName = python,
                WorkingDirectory = root,
                MainArgument = $"-u \"{Path.Combine(root, "tests/localization/stdio_fixture.py")}\""
            };
            var error = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
            fixture.Outputted += text => { if (text == payload) error.TrySetResult(text); };
            try
            {
                Check(fixture.StartBackend(""), "Start echo fixture");
                Check(await fixture.SendInputAndWaitOutputAsync(payload) == payload, "UTF-8 stdin/stdout round trip");
                Check(await error.Task.WaitAsync(TimeSpan.FromSeconds(10)) == payload, "UTF-8 stderr round trip");
            }
            finally
            {
                fixture.StopBackend();
                Environment.SetEnvironmentVariable("PYTHONIOENCODING", oldEncoding);
                Environment.SetEnvironmentVariable("PYTHONUTF8", oldUtf8);
            }
        }
    }

    private static void CheckViews(string output)
    {
        foreach (var language in new[] { 0, 1, 2 })
        {
            UiText.ApplyCulture(language);
            SukiTheme.GetInstance().Locale = UiText.CultureFor(language).Name;
            if (language == 2) RussianTypography.Apply(Application.Current!, language);
            foreach (var theme in new[] { ThemeVariant.Light, ThemeVariant.Dark })
            {
                Application.Current!.RequestedThemeVariant = theme;
                SukiTheme.GetInstance().ChangeBaseTheme(theme);
                foreach (var width in new[] { 800, 1024 })
                {
                    foreach (var page in new[] { "settings", "console", "currency-wars", "extensions" })
                    {
                        Control content = page switch
                        {
                            "settings" => new SettingsPageView(),
                            "console" => new ConsolePageView(),
                            "currency-wars" => new CosmicStrife(),
                            _ => ExtensionFixture()
                        };
                        var window = new SukiWindow
                        {
                            Width = width, Height = 700, Content = content,
                            BackgroundAnimationEnabled = false, TitleBarAnimationEnabled = false
                        };
                        window.Show();
                        Dispatcher.UIThread.RunJobs();
                        window.UpdateLayout();
                        Check(content.Bounds.Width > 0 && content.Bounds.Height > 0, $"Layout {page}");
                        var text = content.GetVisualDescendants().OfType<TextBlock>().Where(node => !string.IsNullOrEmpty(node.Text)).ToArray();
                        Check(text.Length > 0, $"Text controls {page}");
                        if (language == 2)
                            Check(text.Any(node => node.Text!.Any(ch => ch is >= 'А' and <= 'я')), $"Cyrillic text {page}");
                        if (language == 2 && page == "settings")
                        {
                            var label = text.First(node => node.Text == Resources.RetryAfterTaskFailureText);
                            Check(label.TextWrapping == TextWrapping.Wrap, "Long settings label wraps");
                        }
                        if (language == 2 && page == "console")
                        {
                            var hint = text.Single(node => node.Text == ExtraResources.U0418);
                            Check(hint.TextWrapping == TextWrapping.Wrap, "Long console instruction wraps");
                            Check(hint.Bounds.Width > 0 && hint.Bounds.Right <= content.Bounds.Width, "Console instruction fits");
                            foreach (var filter in text.Where(node => node.Text is "Trace" or "Debug" or "Info" or "Warn" or "Error"))
                                Check(filter.TextLayout.Height <= filter.Bounds.Height + 1, "Console filter text height");
                        }
                        using var bitmap = new RenderTargetBitmap(new PixelSize(width, 700), new Vector(96, 96));
                        bitmap.Render(window);
                        bitmap.Save(Path.Combine(output, $"{language}-{theme.Key}-{width}-{page}.png"), PngBitmapEncoderOptions.Default);
                        window.Close();
                    }
                }
            }
        }
        var typeface = new Typeface("Segoe UI").GlyphTypeface;
        foreach (var ch in "РусскийЯяЁё")
            Check(typeface.CharacterToGlyphMap.TryGetGlyph(ch, out var glyph) && glyph != 0, $"Cyrillic glyph U+{(int)ch:X4}");
    }

    private static Control ExtensionFixture()
    {
        var model = new ExtensionConfigDialogViewModel("CurrencyWarsPlus", null!) { IsLoading = false };
        model.Fields.Add(new StringFieldViewModel
        {
            Key = "开拓者名称", Label = UiText.T("开拓者名称"),
            Description = UiText.T("填写游戏内开拓者名称。"), Value = "Тест"
        });
        model.Fields.Add(new IntegerFieldViewModel
        {
            Key = "运行次数", Label = UiText.T("运行次数"),
            Description = UiText.T("本次运行的局数。"), Value = 1, Minimum = 1, Maximum = 99999
        });
        return new ExtensionConfigDialogView { DataContext = model };
    }
}

public sealed class LocalizationApp : Application
{
    public override void Initialize()
    {
        Styles.Add(new StyleInclude(new Uri("avares://SRA/"))
        {
            Source = new Uri("avares://SRA/Styles/Styles.axaml")
        });
        Styles.Add(new SukiTheme { Locale = "zh-CN" });
        Resources["Phosphor"] = new FontFamily("avares://SRA/Assets/Phosphor.ttf#Phosphor");
    }
}

internal sealed class EchoBackend() : LocalBackendService(NullLogger<LocalBackendService>.Instance)
{
    public override string FileName { get; set; } = "";
    public override string WorkingDirectory { get; set; } = "";
    public override string MainArgument { get; set; } = "";
}

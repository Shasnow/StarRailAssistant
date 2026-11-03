using System.Collections;
using System.Globalization;
using System.Resources;
using System.Text.Json;
using SRAFrontend.Desktop;
using SRAFrontend.Desktop.Controls;
using SRAFrontend.Desktop.ViewModels;
using SRAFrontend.Localization;
using SRAFrontend.Models;
using Xunit;

namespace SRALocalizationChecks;

[Collection("Avalonia")]
public sealed class ResourceLocalizationTests(AvaloniaSession session)
{
    [Theory]
    [InlineData(UiLanguage.Chinese, "zh-CN")]
    [InlineData(UiLanguage.English, "en-US")]
    [InlineData(UiLanguage.Russian, "ru-RU")]
    public void Culture_follows_ui_language(UiLanguage language, string expected)
    {
        session.Run(() =>
        {
            var originalCulture = CultureInfo.CurrentCulture;
            var originalDefaultCulture = CultureInfo.DefaultThreadCurrentCulture;
            try
            {
                // 预先设成与目标无关的文化，确认 ConfigureCulture 会覆盖而不是沿用
                CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo("en-US");
                CultureInfo.DefaultThreadCurrentCulture = CultureInfo.GetCultureInfo("ja-JP");
                App.ConfigureCulture(language);
                Assert.Equal(expected, CultureInfo.CurrentCulture.Name);
                Assert.Equal(expected, CultureInfo.DefaultThreadCurrentCulture.Name);
                Assert.Equal(expected, Resources.Culture?.Name);
            }
            finally
            {
                CultureInfo.CurrentCulture = originalCulture;
                CultureInfo.DefaultThreadCurrentCulture = originalDefaultCulture;
            }
        });
    }

    [Theory]
    [InlineData(UiLanguage.Chinese, "2026年11月02日")]
    [InlineData(UiLanguage.English, "Monday, November 2, 2026")]
    [InlineData(UiLanguage.Russian, "ноября")]
    public void Date_format_follows_ui_language(UiLanguage language, string expected)
    {
        session.Run(() =>
        {
            // 格式串与文化必须同时跟随界面语言，否则会出现「Monday, 十一月 2, 2026」这类混排
            App.ConfigureCulture(language);
            var date = new DateTime(2026, 11, 2);
            var formatted = (string)DateToStringConverter.Instance.Convert(
                date, typeof(string), null, CultureInfo.InvariantCulture)!;
            Assert.Contains(expected, formatted);
        });
    }

    [Fact]
    public void Russian_formatting_uses_ui_culture()
    {
        session.Run(() =>
        {
            App.ConfigureCulture(UiLanguage.Russian);
            Assert.Equal("Осталось: 1,5 ч.", string.Format(Resources.Culture, Resources.RemainingHoursFormat, 1.5));
            Assert.Equal("Осталось: 2 дн. 3 ч.",
                string.Format(Resources.Culture, Resources.RemainingDaysHoursFormat, 2, 3));
            Assert.StartsWith("Это не", Resources.NotSequenceReadArchiveText);
        });
    }

    [Fact]
    public void Enum_labels_localize_without_changing_alias_or_value()
    {
        session.Run(() =>
        {
            App.ConfigureCulture(UiLanguage.Russian);
            var field = new EnumFieldViewModel { Key = "难度", Label = Resources.DifficultyLabelText };
            field.SetValue(JsonSerializer.SerializeToElement(2));
            field.UpdateOptions(new[] { 0, 1, 2 }.Select(value => JsonSerializer.SerializeToElement(value)).ToArray(),
                new[] { Resources.DifficultyLowestText, Resources.DifficultyHighestText, Resources.DifficultyCurrentText });
            Assert.Equal("难度", field.Key);
            Assert.Equal(2, field.GetValueAsJson().GetInt32());
            Assert.Equal("Текущая", field.SelectedOption?.Label);

            App.ConfigureCulture(UiLanguage.Chinese);
            Assert.Equal("最低难度", Resources.DifficultyLowestText);
            App.ConfigureCulture(UiLanguage.English);
            Assert.NotEqual("最低难度", Resources.DifficultyLowestText);
        });
    }

    [Theory]
    [InlineData(UiLanguage.Chinese)]
    [InlineData(UiLanguage.English)]
    [InlineData(UiLanguage.Russian)]
    public void Settings_language_round_trips(UiLanguage language)
    {
        var settings = new AppSettings();
        settings.Display.Language = language;
        var path = Path.Combine(TestEnvironment.OutputDirectory, $"settings-{(int)language}.json");
        File.WriteAllText(path, JsonSerializer.Serialize(settings));
        var restored = JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(path))!;
        Assert.Equal(language, restored.Display.Language);
    }

    [Fact]
    public void Satellite_resources_cover_every_chinese_key()
    {
        var manager = new ResourceManager("SRAFrontend.Localization.Resources", typeof(Resources).Assembly);
        var source = manager.GetResourceSet(CultureInfo.GetCultureInfo("zh-CN"), true, true)!;
        var neutral = manager.GetResourceSet(CultureInfo.GetCultureInfo("en-US"), true, true)!;
        var russian = manager.GetResourceSet(CultureInfo.GetCultureInfo("ru-RU"), true, true)!;
        var missing = new List<string>();
        foreach (DictionaryEntry item in source)
        {
            var key = (string)item.Key;
            if (neutral.GetString(key) is null) missing.Add($"en-US:{key}");
            if (russian.GetString(key) is null) missing.Add($"ru-RU:{key}");
        }
        Assert.Empty(missing);
    }
}

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Resources;

namespace SRAFrontend.Localization;

/// <summary>Presentation-only localization. Never use translated text as a stored value or identifier.</summary>
public static class UiText
{
    private static readonly ResourceManager Manager = new("SRAFrontend.Localization.ExtraResources", typeof(UiText).Assembly);
    private static readonly Lazy<Dictionary<string, string>> SourceKeys = new(() =>
    {
        var result = new Dictionary<string, string>(StringComparer.Ordinal);
        var set = Manager.GetResourceSet(CultureInfo.GetCultureInfo("zh-CN"), true, true);
        if (set != null)
            foreach (System.Collections.DictionaryEntry item in set)
                if (item.Value is string source && item.Key is string key)
                    result.TryAdd(Normalize(source), key);
        return result;
    });

    public static CultureInfo CultureFor(int language) => CultureInfo.GetCultureInfo(language switch
    {
        1 => "en-US",
        2 => "ru-RU",
        _ => "zh-CN"
    });

    public static void ApplyCulture(int language)
    {
        var culture = CultureFor(language);
        Resources.Culture = culture;
        // 仅切换界面语言，保留数字和日期解析所用的运行时区域设置。
        CultureInfo.CurrentUICulture = culture;
        CultureInfo.DefaultThreadCurrentUICulture = culture;
    }

    public static string Get(string key) => Manager.GetString(key, Resources.Culture) ?? key;

    private static string Normalize(string value) => value.Replace("\r\n", "\n");

    public static string T(string? source)
    {
        if (source == null) return "";
        if (Resources.Culture?.Name != "ru-RU") return source;
        return SourceKeys.Value.TryGetValue(Normalize(source), out var key) ? Get(key) : source;
    }

    public static string F(FormattableString source)
    {
        if (Resources.Culture?.Name != "ru-RU") return source.ToString(CultureInfo.CurrentCulture);
        var format = T(source.Format);
        var args = source.GetArguments().Select(value => value is string text ? T(text) : value).ToArray();
        return string.Format(Resources.Culture, format, args);
    }
}

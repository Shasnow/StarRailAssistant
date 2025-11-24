using System;
using System.Globalization;
using Avalonia.Data.Converters;
using SRAFrontend.Localization;

namespace SRAFrontend.Utilities;

public class HotkeyDisplayConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        var s = value as string;
        if (string.IsNullOrWhiteSpace(s)) return Resources.NotSetText; // Placeholder when not set (localized)

        // Normalize (some values may already be literal characters)
        return s switch
        {
            "OemMinus" => "-",
            "OemPlus" => "+", // might be '=' on some layouts
            "OemComma" => ",",
            "OemPeriod" => ".",
            "Oem2" => "/",        // slash or question mark
            "Oem3" => "`",         // backtick/tilde
            "Oem4" => "[",
            "Oem5" => "\\",
            "Oem6" => "]",
            "Oem7" => "'",
            "Oem1" => ";",        // semicolon/colon
            "Space" => "Space",
            "Tab" => "Tab",
            "Enter" => "Enter",
            "Escape" => "Esc",
            "Back" => "Backspace",
            _ => s
        };
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        var s = value as string;
        if (string.IsNullOrWhiteSpace(s) || s == Resources.NotSetText) return string.Empty;
        // Reverse map for known literals
        return s switch
        {
            "-" => "OemMinus",
            "+" => "OemPlus",
            "," => "OemComma",
            "." => "OemPeriod",
            "/" => "Oem2",
            "`" => "Oem3",
            "[" => "Oem4",
            "\\" => "Oem5",
            "]" => "Oem6",
            "'" => "Oem7",
            ";" => "Oem1",
            "Space" => "Space",
            "Tab" => "Tab",
            "Enter" => "Enter",
            "Esc" => "Escape",
            "Backspace" => "Back",
            _ => s
        };
    }
}

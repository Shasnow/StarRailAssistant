using System;
using System.Globalization;
using Avalonia.Data.Converters;

namespace SRAFrontend.Utils;

/// <summary>将整型与 ConverterParameter（字符串整数）比较，用于策略相关控件的 IsVisible。</summary>
public class IntEqualsToBoolConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (!TryToInt(value, out var i))
            return false;
        if (parameter is not string s || !int.TryParse(s, NumberStyles.Integer, culture, out var p))
            return false;
        return i == p;
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        throw new NotSupportedException();

    private static bool TryToInt(object? value, out int i)
    {
        switch (value)
        {
            case int x:
                i = x;
                return true;
            case long x:
                i = (int)x;
                return true;
            default:
                return int.TryParse(value?.ToString(), NumberStyles.Integer, CultureInfo.InvariantCulture, out i);
        }
    }
}

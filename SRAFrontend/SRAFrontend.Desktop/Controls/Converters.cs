using System;
using System.Globalization;
using Avalonia.Data.Converters;
using SRAFrontend.Localization;

namespace SRAFrontend.Desktop.Controls;

public class ZeroToBooleanConverter : IValueConverter
{
    public static readonly ZeroToBooleanConverter Instance = new();

    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is int count)
            return count == 0;
        return true;
    }

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotSupportedException();
    }
}

public class GlobalChannelConverter : IValueConverter
{
    public static readonly GlobalChannelConverter Instance = new();

    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        return value is int channel && channel == 2;
    }

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotSupportedException();
    }
}

public class DateToStringConverter : IValueConverter
{
    public static readonly DateToStringConverter Instance = new();

    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is DateTime dt)
            return dt.ToString(Resources.DateDisplayFormat,
                SRAFrontend.Localization.Resources.Culture?.Name == "ru-RU"
                    ? SRAFrontend.Localization.Resources.Culture : new CultureInfo("zh-CN"));
        return "";
    }

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotSupportedException();
    }
}

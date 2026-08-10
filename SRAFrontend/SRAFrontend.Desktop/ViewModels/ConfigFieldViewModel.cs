using System.Text.Json;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Desktop.ViewModels;

/// <summary>
/// 表单字段基类，仅携带通用元数据。
/// 具体值属性和控件通过子类 + DataTemplate 按类型动态生成，
/// 避免 IsVisible 隐藏时仍创建不必要的控件实例。
/// </summary>
public abstract partial class ConfigFieldViewModel : ObservableObject
{
    [ObservableProperty] private string _key = "";
    [ObservableProperty] private string _label = "";
    [ObservableProperty] private string _description = "";
    public bool HasDescription => !string.IsNullOrWhiteSpace(Description);
    public abstract JsonElement GetValueAsJson();
}

public partial class StringFieldViewModel : ConfigFieldViewModel
{
    [ObservableProperty] private string _value = "";

    public override JsonElement GetValueAsJson()
    {
        var json = JsonSerializer.Serialize(Value);
        return JsonDocument.Parse(json).RootElement.Clone();
    }
}

public partial class IntegerFieldViewModel : ConfigFieldViewModel
{
    [ObservableProperty] private long _value;
    [ObservableProperty] private decimal _minimum = decimal.MinValue;
    [ObservableProperty] private decimal _maximum = decimal.MaxValue;

    public override JsonElement GetValueAsJson()
    {
        var json = JsonSerializer.Serialize(Value);
        return JsonDocument.Parse(json).RootElement.Clone();
    }
}

public partial class BooleanFieldViewModel : ConfigFieldViewModel
{
    [ObservableProperty] private bool _value;

    public override JsonElement GetValueAsJson()
    {
        var json = JsonSerializer.Serialize(Value);
        return JsonDocument.Parse(json).RootElement.Clone();
    }
}

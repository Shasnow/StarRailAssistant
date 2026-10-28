using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

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

/// <summary>下拉选项保留原始 JSON 值，显示名称与配置值分别保存。</summary>
public sealed class EnumOption(string label, JsonElement value)
{
    public string Label { get; } = label;
    public JsonElement Value { get; } = value.Clone();
}

// ssyb：选项刷新保留当前真实值，避免覆盖尚未保存的配置。
public partial class EnumFieldViewModel : ConfigFieldViewModel
{
    private readonly List<EnumOption> _availableOptions = [];
    private JsonElement _currentValue = JsonSerializer.SerializeToElement("");
    private bool _isSynchronizing;

    [ObservableProperty] private EnumOption? _selectedOption;
    [ObservableProperty] private string _rawText = "";
    [ObservableProperty] private bool _allowCustom;
    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(RefreshOptionsCommand))]
    private bool _refreshable;
    [ObservableProperty] private string _refreshLabel = global::SRAFrontend.Localization.UiText.T("扫描");
    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(RefreshOptionsCommand))]
    private bool _isRefreshing;
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(HasRefreshError))]
    private string _refreshError = "";
    [ObservableProperty] private string _optionsStatus = "";

    public ObservableCollection<EnumOption> Options { get; } = [];
    public bool HasRefreshError => !string.IsNullOrWhiteSpace(RefreshError);
    public Func<EnumFieldViewModel, Task>? RefreshOptionsRequested { get; set; }

    public void SetValue(JsonElement value)
    {
        _currentValue = value.Clone();
        SynchronizeOptions();
    }

    public void UpdateOptions(IReadOnlyList<JsonElement> values, IReadOnlyList<string>? labels)
    {
        // 先构造新选项，再替换旧列表；扫描失败时旧列表仍可继续使用。
        var options = new List<EnumOption>();
        for (var index = 0; index < values.Count; index++)
        {
            var value = values[index];
            var label = labels?.Count == values.Count ? labels[index] : ValueText(value);
            options.Add(new EnumOption(SRAFrontend.Localization.UiText.T(label), value));
        }

        _availableOptions.Clear();
        _availableOptions.AddRange(options);
        SynchronizeOptions();
        OptionsStatus = global::SRAFrontend.Localization.UiText.F($"可选项：{options.Count} 个");
    }

    private void SynchronizeOptions()
    {
        _isSynchronizing = true;
        try
        {
            Options.Clear();
            foreach (var option in _availableOptions)
                Options.Add(option);
            var selected = Options.FirstOrDefault(option => JsonElement.DeepEquals(option.Value, _currentValue));
            if (selected == null)
            {
                // 新扫描未包含已选文件或自定义路径时，保留当前配置供用户检查。
                var text = ValueText(_currentValue);
                selected = new EnumOption(global::SRAFrontend.Localization.UiText.F($"{(text.Length == 0 ? "（空）" : text)}（当前值）"), _currentValue);
                Options.Add(selected);
            }
            SelectedOption = selected;
            RawText = ValueText(_currentValue);
        }
        finally
        {
            _isSynchronizing = false;
        }
    }

    partial void OnSelectedOptionChanged(EnumOption? value)
    {
        if (_isSynchronizing || value == null)
            return;
        _currentValue = value.Value.Clone();
        // 控件正在提交选择时不修改选项集合，避免选中索引因列表重建失效。
        _isSynchronizing = true;
        try
        {
            RawText = ValueText(_currentValue);
        }
        finally
        {
            _isSynchronizing = false;
        }
    }

    partial void OnRawTextChanged(string value)
    {
        if (_isSynchronizing || !AllowCustom)
            return;
        _currentValue = JsonSerializer.SerializeToElement(value);
        SynchronizeOptions();
    }

    private static string ValueText(JsonElement value) =>
        value.ValueKind == JsonValueKind.String ? value.GetString() ?? "" : value.ToString();

    private bool CanRefreshOptions() => Refreshable && !IsRefreshing;

    [RelayCommand(CanExecute = nameof(CanRefreshOptions))]
    private async Task RefreshOptionsAsync()
    {
        if (!CanRefreshOptions() || RefreshOptionsRequested == null)
            return;
        IsRefreshing = true;
        RefreshError = "";
        try
        {
            await RefreshOptionsRequested(this);
        }
        catch (Exception error)
        {
            RefreshError = global::SRAFrontend.Localization.UiText.F($"扫描失败：{error.Message}");
        }
        finally
        {
            IsRefreshing = false;
        }
    }

    public override JsonElement GetValueAsJson() => _currentValue.Clone();
}

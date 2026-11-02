using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SRAFrontend.Localization;

namespace SRAFrontend.Desktop.ViewModels;

public partial class ExtensionConfigDialogViewModel : ObservableObject
{
    private readonly string _extensionId;
    private readonly IBackendService _backendService;

    [ObservableProperty] private bool _isLoading = true;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(HasRefreshError))]
    private string _refreshError = "";

    public bool HasRefreshError => !string.IsNullOrWhiteSpace(RefreshError);

    public ObservableCollection<ConfigFieldViewModel> Fields { get; } = [];

    public ExtensionConfigDialogViewModel(string extensionId, IBackendService backendService)
    {
        _extensionId = extensionId;
        _backendService = backendService;
    }

    public async Task LoadAsync()
    {
        IsLoading = true;
        try
        {
            var schema = await _backendService.GetExtensionSchemaAsync(_extensionId);
            if (schema == null)
            {
                IsLoading = false;
                return;
            }

            var configValues = new Dictionary<string, JsonElement>();
            var configJson = await _backendService.GetExtensionConfigAsync(_extensionId);
            if (!string.IsNullOrWhiteSpace(configJson))
            {
                using var doc = JsonDocument.Parse(configJson);
                foreach (var prop in doc.RootElement.EnumerateObject())
                    configValues[prop.Name] = prop.Value.Clone();
            }

            Fields.Clear();
            foreach (var (key, prop) in schema.Properties)
            {
                var field = CreateFieldByType(key, prop);
                var defaultElement = JsonSerializer.SerializeToElement(prop.Default);
                if (configValues.TryGetValue(key, out var currentVal) &&
                    currentVal.ValueKind != JsonValueKind.Undefined)
                    ApplyValue(field, currentVal);
                else if (defaultElement.ValueKind != JsonValueKind.Undefined)
                    ApplyValue(field, defaultElement);

                Fields.Add(field);
            }
        }
        finally
        {
            IsLoading = false;
        }
    }

    private ConfigFieldViewModel CreateFieldByType(string key, ExtensionSchemaProperty prop)
    {
        // Yukki：枚举优先于基础类型，难度数字仍按数字保存。
        // 空枚举也保留下拉和自定义输入，方便用户添加攻略后刷新选项。
        if (prop.Enum != null)
        {
            var field = new EnumFieldViewModel
            {
                Key = key, Label = string.IsNullOrEmpty(prop.Title) ? key : prop.Title, Description = prop.Description,
                AllowCustom = prop.AllowCustom && prop.Type == "string"
            };
            field.UpdateOptions(prop.Enum, prop.EnumLabels);
            return field;
        }

        // 根据字段类型创建对应的子类，确保只实例化一个控件模板，
        // 而不是把三种控件都创建出来再用 IsVisible 隐藏。
        return prop.Type switch
        {
            "integer" => new IntegerFieldViewModel
            {
                Key = key, Label = string.IsNullOrEmpty(prop.Title) ? key : prop.Title, Description = prop.Description,
                Minimum = prop.Minimum ?? decimal.MinValue,
                Maximum = prop.Maximum ?? decimal.MaxValue
            },
            "boolean" => new BooleanFieldViewModel
            {
                Key = key, Label = string.IsNullOrEmpty(prop.Title) ? key : prop.Title, Description = prop.Description
            },
            _ => new StringFieldViewModel
            {
                Key = key, Label = string.IsNullOrEmpty(prop.Title) ? key : prop.Title, Description = prop.Description
            }
        };
    }

    /// <summary>重新读取 schema，只更新枚举字段的可选项，保留当前值与未保存的修改。</summary>
    [RelayCommand]
    private async Task RefreshAsync()
    {
        if (IsLoading) return;
        IsLoading = true;
        RefreshError = "";
        try
        {
            var schema = await _backendService.GetExtensionSchemaAsync(_extensionId);
            if (schema == null)
            {
                RefreshError = Resources.OptionsBackendErrorMessage;
                return;
            }

            foreach (var field in Fields.OfType<EnumFieldViewModel>())
                if (schema.Properties.TryGetValue(field.Key, out var prop) && prop.Enum != null)
                    field.UpdateOptions(prop.Enum, prop.EnumLabels);
        }
        catch (Exception error)
        {
            RefreshError = string.Format(Resources.Culture, Resources.RefreshFailedError, error.Message);
        }
        finally
        {
            IsLoading = false;
        }
    }

    private static void ApplyValue(ConfigFieldViewModel field, JsonElement value)
    {
        switch (field)
        {
            case EnumFieldViewModel ef:
                ef.SetValue(value);
                break;
            case StringFieldViewModel sf:
                sf.Value = value.ValueKind == JsonValueKind.String
                    ? value.GetString() ?? ""
                    : value.ToString();
                break;
            case IntegerFieldViewModel iF:
                if (value.TryGetInt64(out var l))
                    iF.Value = l;
                break;
            case BooleanFieldViewModel bf:
                bf.Value = value.ValueKind == JsonValueKind.True;
                break;
        }
    }

    public async Task SaveAsync()
    {
        var dict = new Dictionary<string, JsonElement>();
        foreach (var field in Fields)
            dict[field.Key] = field.GetValueAsJson();
        var json = JsonSerializer.Serialize(dict);
        await _backendService.SendInputAsync($"extension config set {_extensionId} {json}");
    }
}

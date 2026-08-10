using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Text.Json;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.Desktop.ViewModels;

public partial class ExtensionConfigDialogViewModel : ObservableObject
{
    private readonly string _extensionId;
    private readonly IBackendService _backendService;

    [ObservableProperty] private bool _isLoading = true;

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
                ConfigFieldViewModel field = CreateFieldByType(key, prop);

                if (configValues.TryGetValue(key, out var currentVal) &&
                    currentVal.ValueKind != JsonValueKind.Undefined)
                    ApplyValue(field, currentVal);
                else if (prop.Default.HasValue && prop.Default.Value.ValueKind != JsonValueKind.Undefined)
                    ApplyValue(field, prop.Default.Value);

                Fields.Add(field);
            }
        }
        finally
        {
            IsLoading = false;
        }
    }

    private static ConfigFieldViewModel CreateFieldByType(string key, ExtensionSchemaProperty prop)
    {
        // 根据字段类型创建对应的子类，确保只实例化一个控件模板，
        // 而不是把三种控件都创建出来再用 IsVisible 隐藏。
        return prop.Type switch
        {
            "integer" => new IntegerFieldViewModel
            {
                Key = key, Label = key, Description = prop.Description,
                Minimum = prop.Minimum ?? decimal.MinValue,
                Maximum = prop.Maximum ?? decimal.MaxValue
            },
            "boolean" => new BooleanFieldViewModel
            {
                Key = key, Label = key, Description = prop.Description
            },
            _ => new StringFieldViewModel
            {
                Key = key, Label = key, Description = prop.Description
            }
        };
    }

    private static void ApplyValue(ConfigFieldViewModel field, JsonElement value)
    {
        switch (field)
        {
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

    [RelayCommand]
    private async Task SaveAsync()
    {
        var dict = new Dictionary<string, JsonElement>();
        foreach (var field in Fields)
            dict[field.Key] = field.GetValueAsJson();
        var json = JsonSerializer.Serialize(dict);
        await _backendService.SendInputAsync($"extension config set {_extensionId} {json}");
    }
}

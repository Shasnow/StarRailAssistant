using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Models;

namespace SRAFrontend.ViewModels;

/// <summary>单个参数的值绑定 ViewModel</summary>
public partial class ScriptParamValueViewModel : ObservableObject
{
    public ScriptParamDef Def { get; }

    public string Key => Def.Key;
    public string Label => !string.IsNullOrEmpty(Def.Label) ? Def.Label : Def.Key;
    public string Description => Def.Description ?? "";
    public bool HasDescription => !string.IsNullOrEmpty(Description);
    public string DefaultValue => Def.Default ?? "";
    public List<string> Options => Def.Options ?? [];

    public bool IsText => Def.Type is "string" or "int" or "number" or null or "";
    public bool IsBool => Def.Type == "bool";
    public bool IsSelect => Def.Type == "select";

    [ObservableProperty] private string _value = "";
    [ObservableProperty] private bool _boolValue;

    public ScriptParamValueViewModel(ScriptParamDef def, string currentValue)
    {
        Def = def;
        if (IsBool)
        {
            _boolValue = currentValue is "true" or "True" or "1";
            _value = _boolValue.ToString().ToLower();
        }
        else
        {
            _value = string.IsNullOrEmpty(currentValue) ? (def.Default ?? "") : currentValue;
        }
    }

    partial void OnBoolValueChanged(bool value) => Value = value.ToString().ToLower();

    public string GetSaveValue() => IsBool ? BoolValue.ToString().ToLower() : Value;
}

/// <summary>参数分组</summary>
public partial class ScriptParamGroupViewModel : ObservableObject
{
    public string GroupName { get; }
    public bool HasGroupName => !string.IsNullOrEmpty(GroupName);
    public AvaloniaList<ScriptParamValueViewModel> Params { get; } = new();

    public ScriptParamGroupViewModel(string groupName = "")
    {
        GroupName = groupName;
    }
}

/// <summary>脚本配置弹窗 ViewModel（由 settings.json 驱动）</summary>
public partial class ScriptConfigWindowViewModel : ObservableObject
{
    private readonly string _scriptId;
    private readonly string _configDir;

    public string Title { get; }
    public bool HasParams { get; }
    public string NoParamsMessage { get; private set; } = "未找到 settings.json，此脚本暂未提供可配置项。";

    public AvaloniaList<ScriptParamGroupViewModel> ParamGroups { get; } = new();

    private static readonly JsonSerializerOptions _json = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        WriteIndented = true
    };

    public ScriptConfigWindowViewModel(
        string scriptId,
        string configDir,
        List<ScriptParamDef> paramDefs)
    {
        _scriptId = scriptId;
        _configDir = configDir;
        Title = $"修改脚本配置 · {scriptId}";

        if (paramDefs.Count == 0)
        {
            HasParams = false;
            NoParamsMessage = "未找到 settings.json，此脚本暂未提供可配置项。\n你可以在脚本目录手动创建 config.json 进行配置。";
            return;
        }

        HasParams = true;

        // 读取现有 config.json
        var existing = LoadExistingConfig();

        // 按分组渲染
        ScriptParamGroupViewModel? currentGroup = null;
        foreach (var def in paramDefs)
        {
            if (def.Type == "group")
            {
                currentGroup = new ScriptParamGroupViewModel(def.Label ?? def.Key);
                ParamGroups.Add(currentGroup);
                continue;
            }

            if (currentGroup == null)
            {
                currentGroup = new ScriptParamGroupViewModel("");
                ParamGroups.Add(currentGroup);
            }

            existing.TryGetValue(def.Key, out var savedValue);
            currentGroup.Params.Add(new ScriptParamValueViewModel(def, savedValue ?? ""));
        }
    }

    private Dictionary<string, string> LoadExistingConfig()
    {
        var path = Path.Combine(_configDir, "config.json");
        if (!File.Exists(path)) return new();
        try
        {
            var root = JsonNode.Parse(File.ReadAllText(path)) as JsonObject;
            if (root == null) return new();
            var result = new Dictionary<string, string>();
            foreach (var kv in root)
                result[kv.Key] = kv.Value?.ToString() ?? "";
            return result;
        }
        catch { return new(); }
    }

    [RelayCommand]
    private void Save()
    {
        var path = Path.Combine(_configDir, "config.json");
        JsonObject root;
        if (File.Exists(path))
        {
            try { root = JsonNode.Parse(File.ReadAllText(path)) as JsonObject ?? new JsonObject(); }
            catch { root = new JsonObject(); }
        }
        else
        {
            Directory.CreateDirectory(_configDir);
            root = new JsonObject();
        }

        foreach (var group in ParamGroups)
            foreach (var param in group.Params)
                root[param.Key] = JsonValue.Create(param.GetSaveValue());

        File.WriteAllText(path, root.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
    }

    [RelayCommand]
    private void OpenFolder()
    {
        if (Directory.Exists(_configDir))
            System.Diagnostics.Process.Start("explorer.exe", _configDir);
    }
}

using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Extensions.Logging;

namespace SRAFrontend.ViewModels;

/// <summary>
/// 脚本 config.json 的键值编辑器 ViewModel。
/// 供 CustomTaskView 中「脚本配置」区域绑定使用。
/// </summary>
public partial class ScriptConfigEditorViewModel : ObservableObject
{
    private readonly ILogger<ScriptConfigEditorViewModel> _logger;
    private string _scriptId = "";
    private string _configPath = "";

    [ObservableProperty] private string _rawJson = "";
    [ObservableProperty] private bool _hasError;
    [ObservableProperty] private string _errorMessage = "";
    [ObservableProperty] private bool _isLoaded;

    public ScriptConfigEditorViewModel(ILogger<ScriptConfigEditorViewModel> logger)
    {
        _logger = logger;
    }

    /// <summary>加载指定脚本的 config.json（不存在则显示空）</summary>
    public void Load(string scriptId)
    {
        _scriptId = scriptId;
        if (string.IsNullOrEmpty(scriptId))
        {
            RawJson = "";
            IsLoaded = false;
            return;
        }

        var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        var scriptDir = Path.Combine(appData, "SRA", "scripts", scriptId);
        _configPath = Path.Combine(scriptDir, "config.json");

        try
        {
            if (File.Exists(_configPath))
            {
                var text = File.ReadAllText(_configPath);
                // 格式化 JSON 以便阅读
                var node = JsonNode.Parse(text);
                RawJson = node?.ToJsonString(new JsonSerializerOptions { WriteIndented = true }) ?? text;
            }
            else
            {
                RawJson = "{}";
            }
            HasError = false;
            ErrorMessage = "";
            IsLoaded = true;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "加载脚本配置失败: {Path}", _configPath);
            RawJson = "{}";
            HasError = true;
            ErrorMessage = $"加载失败: {ex.Message}";
            IsLoaded = true;
        }
    }

    [RelayCommand]
    private void Save()
    {
        if (string.IsNullOrEmpty(_configPath)) return;
        try
        {
            // 验证 JSON 合法性
            JsonNode.Parse(RawJson);
            Directory.CreateDirectory(Path.GetDirectoryName(_configPath)!);
            File.WriteAllText(_configPath, RawJson);
            HasError = false;
            ErrorMessage = "";
        }
        catch (JsonException ex)
        {
            HasError = true;
            ErrorMessage = $"JSON 格式错误: {ex.Message}";
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "保存脚本配置失败: {Path}", _configPath);
            HasError = true;
            ErrorMessage = $"保存失败: {ex.Message}";
        }
    }

    [RelayCommand]
    private void OpenFolder()
    {
        var dir = Path.GetDirectoryName(_configPath);
        if (!string.IsNullOrEmpty(dir) && Directory.Exists(dir))
            System.Diagnostics.Process.Start("explorer.exe", dir);
    }
}

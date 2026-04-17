using System.Collections.Generic;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

/// <summary>脚本仓库配置</summary>
public partial class ScriptRepo : ObservableObject
{
    [ObservableProperty] private string _name = "";
    [ObservableProperty] private string _url = "";
    [ObservableProperty] private bool _enabled = true;
}

/// <summary>脚本内的单个任务定义</summary>
public partial class ScriptTaskDef : ObservableObject
{
    [ObservableProperty] private string _name = "";
    [ObservableProperty] private string _entry = "";
    /// <summary>Python 类名（对应 manifest.json 中的 "class" 字段）</summary>
    [ObservableProperty] private string _class = "";
    /// <summary>兼容旧字段名 ClassName</summary>
    public string ClassName { get => Class; set => Class = value; }
    /// <summary>任务级参数定义（manifest.json tasks[].params）</summary>
    public List<ScriptParamDef> Params { get; set; } = [];
}

/// <summary>本地脚本的 manifest.json 模型</summary>
public partial class ScriptManifest : ObservableObject
{
    [ObservableProperty] private string _id = "";
    [ObservableProperty] private string _name = "";
    [ObservableProperty] private string _version = "";
    [ObservableProperty] private string _description = "";
    [ObservableProperty] private string _author = "";
    [ObservableProperty] private List<ScriptTaskDef> _tasks = [];
    /// <summary>从脚本目录 settings.json 加载的参数定义（优先于 tasks[].params）</summary>
    public List<ScriptParamDef> LoadedParams { get; set; } = [];
}

/// <summary>仓库索引中的脚本信息</summary>
public partial class RepoScriptInfo : ObservableObject
{
    [ObservableProperty] private string _id = "";
    [ObservableProperty] private string _name = "";
    [ObservableProperty] private string _version = "";
    [ObservableProperty] private string _description = "";
    [ObservableProperty] private string _author = "";
    [ObservableProperty] private string _lastUpdated = "";
    [ObservableProperty] private string _downloadUrl = "";
    [ObservableProperty] private string? _installedVersion;
    [ObservableProperty] private bool _hasUpdate;

    public bool IsInstalled => InstalledVersion != null;
}

/// <summary>settings.json 中单个参数的定义</summary>
public class ScriptParamDef
{
    public string Key { get; set; } = "";
    public string? Label { get; set; }
    public string? Type { get; set; }
    public string? Default { get; set; }
    public string? Description { get; set; }
    public List<string>? Options { get; set; }
}

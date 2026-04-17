using System.Collections.Generic;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

/// <summary>
/// 用户配置的一条自定义任务，对应 config.json 中 CustomTasks 数组的一项。
/// Python 后端通过 ScriptId + TaskEntry + TaskClassName 加载对应的任务类。
/// </summary>
public partial class CustomTaskEntry : ObservableObject
{
    [ObservableProperty] private string _id = System.Guid.NewGuid().ToString("N")[..8];
    [ObservableProperty] private string _name = "";
    [ObservableProperty] private string _scriptId = "";
    [ObservableProperty] private string _taskEntry = "";
    [ObservableProperty] private string _taskClassName = "";
    [ObservableProperty] private string _scriptPath = "";
    [ObservableProperty] private bool _isEnabled = true;
    [ObservableProperty] private bool _notifyOnStart;
    [ObservableProperty] private bool _notifyOnComplete;
    /// <summary>任务参数键值对（对应 settings.json 中的各 key）</summary>
    public Dictionary<string, string>? Params { get; set; } = new();
}

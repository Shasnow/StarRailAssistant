using System.Collections.Generic;
using Avalonia.Controls;
using Avalonia.Controls.Templates;
using Avalonia.Metadata;

namespace SRAFrontend.Views.TaskViews;

/// <summary>
///     根据任务类名（如 "StartGameTask"）选择对应的 TaskView。
///     用于 TabControl 动态内容模板，实现 Tab 顺序跟随 TaskOrder 变化。
/// </summary>
public class TaskViewSelector : IDataTemplate
{
    [Content]
    public Dictionary<string, IDataTemplate> Templates { get; } = new();

    public Control? Build(object? param)
    {
        if (param is string key && Templates.TryGetValue(key, out var template))
            return template.Build(param);
        return null;
    }

    public bool Match(object? data) => data is string;
}

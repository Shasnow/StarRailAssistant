using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

/// <summary>
///     排序面板中的任务项，绑定到排序 UI。
/// </summary>
public partial class TaskOrderItem : ObservableObject
{
    /// <summary>任务类名（如 "StartGameTask"），用于与 TaskOrder 同步</summary>
    public string TaskClassName { get; init; } = "";

    /// <summary>显示名称（本地化后的，如 "启动游戏"）</summary>
    public string DisplayName { get; init; } = "";

    /// <summary>是否为固定位置任务（fixed=first/last），固定任务不可移动</summary>
    public bool IsFixed { get; init; }

    /// <summary>是否可向左移动（排序面板绑定）</summary>
    [ObservableProperty] private bool _canMoveLeft;

    /// <summary>是否可向右移动（排序面板绑定）</summary>
    [ObservableProperty] private bool _canMoveRight;
}

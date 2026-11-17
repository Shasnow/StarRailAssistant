using System;

namespace SRAFrontend.Desktop.Models;

/// <summary>命令分组，决定命令面板中的排列顺序（同组内按注册顺序）。</summary>
public enum PaletteCategory
{
    Task,
    Tools,
    View,
    Sra,
    Link,
    Developer
}

/// <summary>
/// 命令面板中的一条命令：标题为本地化名称，副标题为命令标识，右侧可带快捷键提示。
/// </summary>
public sealed class PaletteCommand(string title, string subtitle, PaletteCategory category, string? shortcut = null)
{
    public string Title { get; } = title;
    public string Subtitle { get; } = subtitle;
    public PaletteCategory Category { get; } = category;
    public string? Shortcut { get; } = shortcut;
    public bool HasShortcut => !string.IsNullOrEmpty(Shortcut);
    public Action? Execute { get; init; }
}

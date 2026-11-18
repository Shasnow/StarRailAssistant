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
/// 命令面板中一条命令的元数据（对应 VS Code 的 contributes.commands）：
/// <paramref name="id"/> 是唯一标识，<paramref name="title"/> 为本地化名称，右侧可带快捷键提示。
/// 处理器由 <c>CommandPaletteService.Register</c> 按 ID 绑定，不在元数据上保存。
/// </summary>
public sealed class PaletteCommand(string id, string title, PaletteCategory category, string? shortcut = null)
{
    public string Id { get; } = id;
    public string Title { get; } = title;
    public PaletteCategory Category { get; } = category;
    public string? Shortcut { get; } = shortcut;
    public bool HasShortcut => !string.IsNullOrEmpty(Shortcut);
}

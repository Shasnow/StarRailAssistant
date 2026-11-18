using System;
using System.Collections.Generic;
using System.Linq;
using SRAFrontend.Desktop.Models;

namespace SRAFrontend.Desktop.Services;

/// <summary>
/// 命令注册表（参照 VS Code 的 commands.registerCommand）：
/// 命令以唯一 ID 注册处理器，注册返回的 <see cref="IDisposable"/> 用于注销；
/// 命令面板只读取已注册命令的元数据，执行时按 ID 解析处理器。
/// </summary>
public sealed class CommandPaletteService
{
    private readonly Dictionary<string, Entry> _entries = new(StringComparer.Ordinal);
    private List<PaletteCommand>? _snapshot;
    private long _nextOrder;

    /// <summary>命令集合发生变化（注册/注销）时触发。</summary>
    public event EventHandler? Changed;

    /// <summary>已注册命令的元数据，按分组与注册顺序排列（只读快照）。</summary>
    public IReadOnlyList<PaletteCommand> Commands => _snapshot ??= _entries.Values
        .OrderBy(entry => entry.Command.Category)
        .ThenBy(entry => entry.Order)
        .Select(entry => entry.Command)
        .ToList();

    /// <summary>
    /// 注册命令及其处理器（等价于 VS Code 的 <c>commands.registerCommand(id, handler)</c>）。
    /// 返回的对象释放后会注销该命令。
    /// </summary>
    /// <exception cref="ArgumentException">命令 ID 为空。</exception>
    /// <exception cref="InvalidOperationException">命令 ID 已被注册。</exception>
    public IDisposable Register(PaletteCommand command, Action execute)
    {
        ArgumentNullException.ThrowIfNull(command);
        ArgumentNullException.ThrowIfNull(execute);
        if (string.IsNullOrWhiteSpace(command.Id))
            throw new ArgumentException("命令 ID 不能为空", nameof(command));
        if (!_entries.TryAdd(command.Id, new Entry(command, execute, _nextOrder++)))
            throw new InvalidOperationException($"命令 '{command.Id}' 已注册");

        Invalidate();
        return new Registration(this, command.Id);
    }

    /// <summary>按 ID 执行命令（等价于 <c>commands.executeCommand</c>）；未注册时返回 false。</summary>
    public bool Execute(string id)
    {
        if (!_entries.TryGetValue(id, out var entry)) return false;
        entry.Execute();
        return true;
    }

    private void Unregister(string id)
    {
        if (!_entries.Remove(id)) return;
        Invalidate();
    }

    private void Invalidate()
    {
        _snapshot = null;
        Changed?.Invoke(this, EventArgs.Empty);
    }

    private sealed record Entry(PaletteCommand Command, Action Execute, long Order);

    private sealed class Registration(CommandPaletteService owner, string id) : IDisposable
    {
        private bool _disposed;

        public void Dispose()
        {
            if (_disposed) return;
            _disposed = true;
            owner.Unregister(id);
        }
    }
}

using System;
using System.Collections.Generic;
using SRAFrontend.Desktop.Models;

namespace SRAFrontend.Desktop.Services;

/// <summary>
/// 命令面板的命令注册表。各视图模型在构造时注册自己的命令，
/// 命令面板从 <see cref="Commands"/> 取当前可用的命令集合。
/// </summary>
public sealed class CommandPaletteService
{
    private readonly List<PaletteCommand> _commands = [];

    public IReadOnlyList<PaletteCommand> Commands => _commands;

    /// <summary>命令集合发生变化（注册）时触发。</summary>
    public event EventHandler? Changed;

    public void Register(PaletteCommand command)
    {
        _commands.Add(command);
        Changed?.Invoke(this, EventArgs.Empty);
    }
}

using System;
using Microsoft.Extensions.Logging;

namespace SRAFrontend.Services;

/// <summary>
/// 开发者自定义后端：默认使用 PATH 中的系统 python 运行 main.py，可由设置覆盖命令、参数与工作目录。
/// </summary>
public class CustomBackendService(ILogger<LocalBackendService> logger) : LocalBackendService(logger)
{
    public override string FileName { get; set; } = "python";
    public override string WorkingDirectory { get; set; } = Environment.CurrentDirectory;
    public override string MainArgument { get; set; } = "main.py";
}

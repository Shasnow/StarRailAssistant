using System.Collections.Generic;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;

namespace SRAFrontend.Services;

/// <summary>
/// 默认后端：发布包内嵌的 Python 运行时（<c>AppRoot/python/python.exe</c>）运行源码入口 <c>main.py</c>。
/// </summary>
public class BundledBackendService(ILogger<LocalBackendService> logger) : LocalBackendService(logger)
{
    public override string FileName { get; set; } = DataPath.PythonExe;

    // tasks/ 与 resources/ 通过相对路径加载，工作目录必须是应用根目录
    public override string WorkingDirectory { get; set; } = DataPath.AppRoot;

    public override string MainArgument { get; set; } = "main.py";

    // 内嵌运行时启用了 site，会把用户级 site-packages（%APPDATA%\Python\Python3xx）纳入 sys.path，
    // 可能覆盖随包分发的依赖版本；与 SRA-cli.exe 启动器保持一致地禁用
    public override IReadOnlyDictionary<string, string>? EnvironmentVariables { get; } =
        new Dictionary<string, string> { ["PYTHONNOUSERSITE"] = "1" };
}

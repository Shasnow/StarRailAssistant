using System;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;

namespace SRAFrontend.Services;

public class PyBackendService(ILogger<LocalBackendService> logger) : LocalBackendService(logger)
{
    public override string FileName { get; set; } = PathString.PythonExe;
    public override string WorkingDirectory { get; set; } = Environment.CurrentDirectory;
    public override string MainArgument { get; set; } = "main.py";
}
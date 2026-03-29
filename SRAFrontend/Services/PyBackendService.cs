using System;
using Microsoft.Extensions.Logging;

namespace SRAFrontend.Services;

public class PyBackendService(ILogger<LocalBackendService> logger) : LocalBackendService(logger)
{
    public override string FileName { get; set; } = "python.exe";
    public override string WorkingDirectory { get; set; } = Environment.CurrentDirectory;
    public override string MainArgument { get; set; } = "main.py";
}
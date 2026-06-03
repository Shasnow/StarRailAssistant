using System;
using System.IO;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;

namespace SRAFrontend.Services;

public class CliBackendService(ILogger<LocalBackendService> logger) : LocalBackendService(logger)
{
    public override string FileName { get; set; } = Path.Combine(PathString.AppRoot, "SRA-cli.exe");
    public override string WorkingDirectory { get; set; } = Environment.CurrentDirectory;
    public override string MainArgument { get; set; } = string.Empty;
}
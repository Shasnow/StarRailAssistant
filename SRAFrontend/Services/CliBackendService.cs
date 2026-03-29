using System;
using Microsoft.Extensions.Logging;

namespace SRAFrontend.Services;

public class CliBackendService(ILogger<LocalBackendService> logger) : LocalBackendService(logger)
{
    public override string FileName { get; set; } = "SRA-cli.exe";
    public override string WorkingDirectory { get; set; } = Environment.CurrentDirectory;
    public override string MainArgument { get; set; } = string.Empty;
}
using Microsoft.Extensions.Logging.Abstractions;
using SRAFrontend.Services;
using Xunit;

namespace SRALocalizationChecks;

/// <summary>
/// 校验桌面端与 Python 后端的三条管道（stdin/stdout/stderr）在非 UTF-8 控制台代码页下仍是 UTF-8。
/// 只启动回显脚本，不触碰真实后端、游戏或用户设置。
/// </summary>
public sealed class BackendPipeTests
{
    private const string Payload = "中文 Русский English ё — → {braces}";

    [Theory]
    [InlineData("cp1251")]
    [InlineData("cp1252")]
    [InlineData("gbk")]
    public async Task Stdio_round_trips_utf8(string codepage)
    {
        var python = TestEnvironment.Python312;
        if (python is null)
        {
            Assert.Fail("找不到 Python 3.12，请通过 SRA_TEST_PYTHON 指定解释器路径");
            return;
        }

        var oldEncoding = Environment.GetEnvironmentVariable("PYTHONIOENCODING");
        var oldUtf8 = Environment.GetEnvironmentVariable("PYTHONUTF8");
        Environment.SetEnvironmentVariable("PYTHONIOENCODING", codepage + ":strict");
        Environment.SetEnvironmentVariable("PYTHONUTF8", "0");
        var fixture = new EchoBackend
        {
            FileName = python,
            WorkingDirectory = TestEnvironment.RepositoryRoot,
            MainArgument = $"-u \"{Path.Combine(TestEnvironment.RepositoryRoot, "tests/localization/stdio_fixture.py")}\""
        };
        var stderr = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
        fixture.Outputted += text =>
        {
            if (text == Payload) stderr.TrySetResult(text);
        };
        try
        {
            Assert.True(fixture.StartBackend(""), "启动回显脚本失败");
            Assert.Equal(Payload, await fixture.SendInputAndWaitOutputAsync(Payload));
            Assert.Equal(Payload, await stderr.Task.WaitAsync(TimeSpan.FromSeconds(10)));
        }
        finally
        {
            fixture.StopBackend();
            Environment.SetEnvironmentVariable("PYTHONIOENCODING", oldEncoding);
            Environment.SetEnvironmentVariable("PYTHONUTF8", oldUtf8);
        }
    }
}

internal sealed class EchoBackend() : LocalBackendService(NullLogger<LocalBackendService>.Instance)
{
    public override string FileName { get; set; } = "";
    public override string WorkingDirectory { get; set; } = "";
    public override string MainArgument { get; set; } = "";
}

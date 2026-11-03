using System.Diagnostics;

namespace SRALocalizationChecks;

/// <summary>
/// 测试外部输入：仓库根目录（从输出目录向上找 pyproject.toml）、Python 3.12 解释器、截图输出目录。
/// </summary>
public static class TestEnvironment
{
    public static string RepositoryRoot { get; } = FindRepositoryRoot();

    public static string OutputDirectory { get; } = CreateOutputDirectory();

    /// <summary>
    /// 依次尝试 SRA_TEST_PYTHON、py -3.12、python，全部失败时返回 null，由用例报错说明如何指定。
    /// </summary>
    public static string? Python312 { get; } = FindPython();

    private static string FindRepositoryRoot()
    {
        for (var dir = new DirectoryInfo(AppContext.BaseDirectory); dir is not null; dir = dir.Parent)
            if (File.Exists(Path.Combine(dir.FullName, "pyproject.toml")))
                return dir.FullName;
        throw new InvalidOperationException("找不到仓库根目录（向上未发现 pyproject.toml）");
    }

    private static string CreateOutputDirectory()
    {
        var configured = Environment.GetEnvironmentVariable("SRA_TEST_OUTPUT");
        var path = string.IsNullOrWhiteSpace(configured)
            ? Path.Combine(Path.GetTempPath(), "sra-localization-checks")
            : Path.GetFullPath(configured);
        Directory.CreateDirectory(path);
        return path;
    }

    private static string? FindPython()
    {
        var configured = Environment.GetEnvironmentVariable("SRA_TEST_PYTHON");
        if (!string.IsNullOrWhiteSpace(configured) && File.Exists(configured)) return configured;
        foreach (var (file, arguments) in new[]
                 {
                     ("py", "-3.12 -c \"import sys; print(sys.executable)\""),
                     ("python", "-c \"import sys; print(sys.executable)\"")
                 })
        {
            try
            {
                using var process = Process.Start(new ProcessStartInfo(file, arguments)
                {
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                });
                if (process is null) continue;
                var output = process.StandardOutput.ReadToEnd().Trim();
                process.WaitForExit();
                if (process.ExitCode == 0 && File.Exists(output)) return output;
            }
            catch (Exception ex) when (ex is System.ComponentModel.Win32Exception or InvalidOperationException)
            {
                // 该候选命令不存在，继续尝试下一个
            }
        }
        return null;
    }
}

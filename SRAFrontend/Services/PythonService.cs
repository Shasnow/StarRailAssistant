using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;

namespace SRAFrontend.Services;

public class PythonService(ILogger<PythonService> logger, IHttpClientFactory httpClientFactory)
{
    private const string PythonVersion = "3.12.10";
    private const string PythonVersionTag = "3.12.10";
    private static readonly string ExpectedPythonVersionPrefix = "3.12";

    private static readonly string EnvOkMarker = Path.Combine(PathString.PythonDir, ".python_env_ok");
    private static readonly string EnvVersionJson = Path.Combine(PathString.PythonDir, "python_env_version.json");
    private static readonly string RequirementsTxt = Path.Combine(AppContext.BaseDirectory, "requirements.txt");

    public static bool IsEnvironmentReady()
    {
        return File.Exists(EnvOkMarker);
    }

    public async Task<bool> EnsureEnvironmentAsync(IProgress<string> progress, CancellationToken cancellationToken = default)
    {
        if (File.Exists(EnvOkMarker))
        {
            logger.LogInformation("Python environment marker found, skipping initialization");
            progress.Report("Python 环境已就绪，跳过初始化");
            return true;
        }

        logger.LogInformation("Python environment marker not found, starting initialization");
        progress.Report("开始初始化 Python 环境...");
        try
        {
            if (!await InitializeAsync(progress, cancellationToken))
                return false;

            await WriteEnvMarkerAsync();
            logger.LogInformation("Python environment initialization completed successfully");
            progress.Report("Python 环境初始化完成");
            return true;
        }
        catch (OperationCanceledException)
        {
            logger.LogWarning("Python environment initialization was cancelled");
            progress.Report("Python 环境初始化已取消");
            throw;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to initialize Python environment");
            progress.Report($"Python 环境初始化失败: {ex.Message}");
            return false;
        }
    }

    public async Task<bool> VerifyEnvironmentAsync(CancellationToken cancellationToken = default)
    {
        if (!File.Exists(PathString.PythonExe))
        {
            logger.LogWarning("Python executable not found at {Path}", PathString.PythonExe);
            return false;
        }

        if (!await VerifyPythonVersionAsync(cancellationToken))
        {
            logger.LogWarning("Python version mismatch, environment needs reinitialization");
            return false;
        }

        return await VerifyDependenciesAsync(cancellationToken);
    }

    private async Task<bool> InitializeAsync(IProgress<string> progress, CancellationToken cancellationToken)
    {
        // ① 检查本地内置 Python
        if (File.Exists(PathString.PythonExe))
        {
            logger.LogInformation("Found existing Python executable, verifying version and dependencies");
            progress.Report("检测到本地内置 Python，进入环境维护流程...");
            if (await VerifyPythonVersionAsync(cancellationToken))
            {
                return await EnsureDependenciesAsync(progress, cancellationToken);
            }
            logger.LogInformation("Existing Python version mismatch, reinitialization needed");
            progress.Report("Python 版本不匹配，需要重新初始化");
        }

        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return await InitializeWindowsAsync(progress, cancellationToken);

        return await InitializeLinuxAsync(progress, cancellationToken);
    }

    private async Task<bool> InitializeWindowsAsync(IProgress<string> progress, CancellationToken cancellationToken)
    {
        // ② 检查系统 Python
        var systemPython = FindSystemPython();
        if (systemPython != null)
        {
            logger.LogInformation("Detected system Python at {Path}, creating virtual environment", systemPython);
            progress.Report($"检测到系统 Python: {systemPython}，创建虚拟环境...");
            return await CreateVenvAsync(systemPython, progress, cancellationToken);
        }

        // ③ 下载 embeddable 便携包
        logger.LogInformation("No suitable system Python found, downloading embeddable package");
        progress.Report("未检测到系统 Python，开始下载 Python 便携包...");
        var zipPath = Path.Combine(PathString.TempDir, $"python-{PythonVersion}-embed-amd64.zip");
        if (!await DownloadPythonAsync(zipPath, progress, cancellationToken))
            return false;

        // ④ 解压便携包
        logger.LogInformation("Extracting Python embeddable package to {Destination}", PathString.PythonDir);
        progress.Report("正在解压 Python 便携包...");
        ExtractZip(zipPath, PathString.PythonDir);

        // ⑤ 修复 python312._pth
        logger.LogInformation("Fixing Python configuration files");
        progress.Report("修复 Python 配置文件...");
        FixPthFile();

        // ⑥ 安装 pip
        logger.LogInformation("Installing pip in the Python environment");
        progress.Report("正在安装 pip...");
        if (!await InstallPipAsync(progress, cancellationToken))
            return false;

        // ⑦ 安装依赖
        return await EnsureDependenciesAsync(progress, cancellationToken);
    }

    private async Task<bool> InitializeLinuxAsync(IProgress<string> progress, CancellationToken cancellationToken)
    {
        // Linux: 检查系统 Python 并创建虚拟环境
        var systemPython = FindSystemPython();
        if (systemPython != null)
        {
            logger.LogInformation("Detected system Python at {Path}", systemPython);
            progress.Report($"检测到系统 Python: {systemPython}，创建虚拟环境...");
            return await CreateVenvAsync(systemPython, progress, cancellationToken);
        }

        progress.Report("未检测到系统 Python 3.12.x，请先安装 Python 3.12");
        logger.LogError("Python 3.12.x not found on system");
        return false;
    }

    private async Task<bool> CreateVenvAsync(string systemPython, IProgress<string> progress, CancellationToken cancellationToken)
    {
        if (Directory.Exists(PathString.PythonDir) && File.Exists(PathString.PythonExe))
            return true;

        logger.LogInformation("Creating virtual environment using system Python: {Python}", systemPython);
        progress.Report("正在创建虚拟环境...");
        var result = await RunProcessAsync(systemPython, $"-m venv \"{PathString.PythonDir}\"", cancellationToken);
        if (result.ExitCode != 0)
        {
            logger.LogError("Failed to create virtual environment: {Error}", result.Error);
            progress.Report($"创建虚拟环境失败: {result.Error}");
            return false;
        }

        return File.Exists(PathString.PythonExe);
    }

    private async Task<bool> DownloadPythonAsync(string zipPath, IProgress<string> progress, CancellationToken cancellationToken)
    {
        var downloadUrl =
            $"https://www.python.org/ftp/python/{PythonVersionTag}/python-{PythonVersion}-embed-amd64.zip";

        Directory.CreateDirectory(PathString.TempDir);

        using var client = httpClientFactory.CreateClient();
        client.Timeout = TimeSpan.FromMinutes(5);

        progress.Report($"正在下载 Python {PythonVersion}...");
        var response = await client.GetAsync(downloadUrl, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
        response.EnsureSuccessStatusCode();

        await using var fs = new FileStream(zipPath, FileMode.Create, FileAccess.Write, FileShare.None);
        await response.Content.CopyToAsync(fs, cancellationToken);
        await fs.FlushAsync(cancellationToken);

        progress.Report("下载完成，正在校验文件...");
        return true;
    }

    private static void ExtractZip(string zipPath, string destination)
    {
        Directory.CreateDirectory(destination);
        ZipFile.ExtractToDirectory(zipPath, destination, overwriteFiles: true);
    }

    private static void FixPthFile()
    {
        var pthFiles = Directory.GetFiles(PathString.PythonDir, "python*._pth");
        foreach (var pthFile in pthFiles)
        {
            var content = File.ReadAllText(pthFile);
            content = content.Replace("#import site", "import site");
            File.WriteAllText(pthFile, content);
        }
    }

    private async Task<bool> InstallPipAsync(IProgress<string> progress, CancellationToken cancellationToken)
    {
        var getPipPath = Path.Combine(PathString.TempDir, "get-pip.py");

        using var client = httpClientFactory.CreateClient();
        progress.Report("正在下载 get-pip.py...");
        var getPipContent = await client.GetStringAsync("https://bootstrap.pypa.io/get-pip.py", cancellationToken);
        await File.WriteAllTextAsync(getPipPath, getPipContent, cancellationToken);

        progress.Report("正在安装 pip...");
        var result = await RunProcessAsync(PathString.PythonExe, $"\"{getPipPath}\"", cancellationToken);
        if (result.ExitCode != 0)
        {
            logger.LogError("Failed to install pip: {Error}", result.Error);
            progress.Report($"安装 pip 失败: {result.Error}");
            return false;
        }

        progress.Report("正在安装基础构建工具...");
        result = await RunProcessAsync(PathString.PythonExe,
            "-m pip install setuptools wheel --no-cache-dir --disable-pip-version-check", cancellationToken);
        if (result.ExitCode == 0) return true;
        logger.LogError("Failed to install setuptools/wheel: {Error}", result.Error);
        progress.Report($"安装 setuptools/wheel 失败: {result.Error}");
        return false;

    }

    private async Task<bool> EnsureDependenciesAsync(IProgress<string> progress, CancellationToken cancellationToken)
    {
        if (!File.Exists(RequirementsTxt))
        {
            logger.LogWarning("requirements.txt not found at {Path}", RequirementsTxt);
            progress.Report("未找到 requirements.txt，跳过依赖安装");
            return true;
        }

        var (missing, mismatched) = await CheckDependenciesAsync(cancellationToken);
        if (missing.Count == 0 && mismatched.Count == 0)
        {
            progress.Report("所有依赖已满足");
            return true;
        }

        if (missing.Count > 0)
            progress.Report($"正在安装缺失依赖: {string.Join(", ", missing.Select(m => m.Name))}");

        if (mismatched.Count > 0)
            progress.Report($"正在更新版本不匹配的依赖: {string.Join(", ", mismatched.Select(m => m.Name))}");

        var result = await RunProcessAsync(PathString.PythonExe,
            $"-m pip install -r \"{RequirementsTxt}\" --disable-pip-version-check --no-cache-dir",
            cancellationToken);
        if (result.ExitCode != 0)
        {
            logger.LogError("Failed to install dependencies: {Error}", result.Error);
            progress.Report($"安装依赖失败: {result.Error}");
            return false;
        }

        progress.Report("依赖安装完成");
        return true;
    }

    private async Task<(List<PackageInfo> Missing, List<PackageInfo> Mismatched)> CheckDependenciesAsync(
        CancellationToken cancellationToken)
    {
        var required = ParseRequirements();
        var installed = await GetInstalledPackagesAsync(cancellationToken);

        var missing = new List<PackageInfo>();
        var mismatched = new List<PackageInfo>();

        foreach (var req in required)
        {
            if (!installed.TryGetValue(req.Name.ToLowerInvariant(), out var installedVersion))
            {
                missing.Add(req);
            }
            else if (installedVersion != req.Version)
            {
                mismatched.Add(req);
            }
        }

        return (missing, mismatched);
    }

    private List<PackageInfo> ParseRequirements()
    {
        var packages = new List<PackageInfo>();
        if (!File.Exists(RequirementsTxt))
            return packages;

        foreach (var line in File.ReadAllLines(RequirementsTxt))
        {
            var trimmed = line.Trim();
            if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith('#') || trimmed.StartsWith('-'))
                continue;

            var parts = trimmed.Split('=', 2);
            if (parts.Length == 2 && parts[1].StartsWith('='))
            {
                packages.Add(new PackageInfo(parts[0].Trim(), parts[1].TrimStart('=').Trim()));
            }
            else
            {
                packages.Add(new PackageInfo(parts[0].Trim(), string.Empty));
            }
        }

        return packages;
    }

    private async Task<Dictionary<string, string?>> GetInstalledPackagesAsync(CancellationToken cancellationToken)
    {
        var result = await RunProcessAsync(PathString.PythonExe, "-m pip list --format=json", cancellationToken);
        if (result.ExitCode != 0)
            return new Dictionary<string, string?>();

        try
        {
            var desOptions = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            var packages = JsonSerializer.Deserialize<List<PackageInfo>>(result.Output, desOptions) ?? [];
            return packages
                .Where(p => !string.IsNullOrEmpty(p.Name))
                .ToDictionary(
                    p => p.Name.ToLowerInvariant(),
                    p => p.Version,
                    StringComparer.OrdinalIgnoreCase);
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Failed to parse pip list output");
            return new Dictionary<string, string?>();
        }
    }

    private async Task<bool> VerifyPythonVersionAsync(CancellationToken cancellationToken)
    {
        var result = await RunProcessAsync(PathString.PythonExe, "--version", cancellationToken);
        if (result.ExitCode != 0) return false;

        var versionStr = result.Output.Trim();
        return versionStr.Contains(ExpectedPythonVersionPrefix);
    }

    private async Task<bool> VerifyDependenciesAsync(CancellationToken cancellationToken)
    {
        var (missing, mismatched) = await CheckDependenciesAsync(cancellationToken);
        if (missing.Count == 0 && mismatched.Count == 0) return true;

        logger.LogWarning("Dependency check failed: {Missing} missing, {Mismatched} mismatched",
            missing.Count, mismatched.Count);
        return false;
    }

    private static string? FindSystemPython()
    {
        var candidates = RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
            ? new[] { "python", "python3", "py" }
            : new[] { "python3.12", "python3", "python" };

        foreach (var candidate in candidates)
        {
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = candidate,
                    Arguments = "--version",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };
                using var process = Process.Start(psi);
                if (process == null) continue;
                process.WaitForExit(5000);
                var output = process.StandardOutput.ReadToEnd().Trim();
                if (output.Contains(ExpectedPythonVersionPrefix) && process.ExitCode == 0)
                    return candidate;
            }
            catch
            {
                // command not found
            }
        }

        return null;
    }

    private async Task<ProcessResult> RunProcessAsync(string fileName, string arguments,
        CancellationToken cancellationToken)
    {
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = fileName,
                Arguments = arguments,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                WorkingDirectory = PathString.PythonDir
            };

            using var process = new Process();
            process.StartInfo = psi;
            process.Start();

            var outputTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
            var errorTask = process.StandardError.ReadToEndAsync(cancellationToken);

            await process.WaitForExitAsync(cancellationToken);

            return new ProcessResult(process.ExitCode, await outputTask, await errorTask);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to run process: {FileName} {Arguments}", fileName, arguments);
            return new ProcessResult(-1, string.Empty, ex.Message);
        }
    }

    private async Task WriteEnvMarkerAsync()
    {
        var envInfo = new
        {
            pythonVersion = PythonVersion,
            createdAt = DateTime.UtcNow.ToString("O"),
            platform = RuntimeInformation.OSDescription
        };

        var json = JsonSerializer.Serialize(envInfo, new JsonSerializerOptions { WriteIndented = true });
        await File.WriteAllTextAsync(EnvVersionJson, json);
        await File.WriteAllTextAsync(EnvOkMarker, DateTime.UtcNow.ToString("O"));
        logger.LogInformation("Python environment marker written");
    }

    private record ProcessResult(int ExitCode, string Output, string Error);

    private record PackageInfo(string Name, string? Version);
    
}
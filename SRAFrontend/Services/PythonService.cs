using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.utilities;
using Version = System.Version;

namespace SRAFrontend.Services;

public class PythonService(ILogger<PythonService> logger, HttpClient httpClient, SettingsService settingsService)
{
    // 常量定义（避免魔法值，便于维护）
    private const string PythonExeName = "python.exe";
    private const string PythonPthFileName = "python312._pth";
    private const string RequirementsFileName = "requirements.txt";
    private const string GetPipFileName = "get-pip.py";
    private const string TargetPythonVersion = "3.12"; // 目标主版本
    private const string GetPipUrl = "https://bootstrap.pypa.io/get-pip.py";
    private const int ProcessExitTimeout = 30000; // 进程退出超时（30秒）

    // 懒加载 Python 路径（避免启动时立即计算）
    private readonly Lazy<string> _pythonPath = new(() => Path.Combine(PathString.PythonDir, PythonExeName));
    private string PythonExePath => _pythonPath.Value;

    /// <summary>
    /// 检查 Python 环境状态（入口方法）
    /// </summary>
    public PythonEnvStatus CheckPythonEnvironment()
    {
        logger.LogInformation("开始检查 Python 环境...");

        try
        {
            if (!CheckPythonInstalled())
            {
                logger.LogWarning("Python 未安装：路径={Path}", PythonExePath);
                return PythonEnvStatus.PythonNotInstalled;
            }

            if (!CheckPythonVersion(out var actualVersion))
            {
                logger.LogWarning("Python 版本不匹配：实际版本={ActualVersion}，要求={TargetVersion}",
                    actualVersion, TargetPythonVersion);
                return PythonEnvStatus.PythonVersionMismatch;
            }

            if (!CheckPipInstalled())
            {
                logger.LogWarning("Pip 未安装");
                return PythonEnvStatus.PipNotInstalled;
            }

            var requirementResult = CheckRequirements();
            if (!requirementResult.AllSatisfied)
            {
                logger.LogWarning("依赖包未满足：缺失{MissingCount}个，版本不匹配{MisMatchCount}个",
                    requirementResult.MissingPackages.Count, requirementResult.VersionMismatchPackages.Count);
                return PythonEnvStatus.RequirementsNotInstalled;
            }

            logger.LogInformation("Python 环境检查通过");
            return PythonEnvStatus.AllSet;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Python 环境检查异常");
            return PythonEnvStatus.PythonNotInstalled; // 异常时默认视为未安装
        }
    }

    #region 环境检查方法（优化后）
    /// <summary>
    /// 检查 Python 是否安装（校验路径+文件存在）
    /// </summary>
    private bool CheckPythonInstalled()
    {
        logger.LogDebug("检查 Python 安装状态：路径={Path}", PythonExePath);
        return Directory.Exists(PathString.PythonDir) && File.Exists(PythonExePath);
    }

    /// <summary>
    /// 检查 Python 版本（精准匹配主版本，返回实际版本）
    /// </summary>
    private bool CheckPythonVersion(out string actualVersion)
    {
        actualVersion = "未知版本";
        try
        {
            logger.LogDebug("检查 Python 版本...");
            var (output, error) = RunPython("--version");

            if (!string.IsNullOrEmpty(error))
            {
                logger.LogWarning("获取 Python 版本失败：{Error}", error);
                return false;
            }

            // 解析版本字符串（格式：Python 3.12.10）
            var parts = output.Trim().Split(' ', StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 2 || !Version.TryParse(parts[1], out var version))
            {
                logger.LogWarning("无法解析 Python 版本字符串：{Output}", output);
                return false;
            }

            actualVersion = parts[1];
            // 精准匹配主版本（3.12.x 均符合）
            return version.Major == int.Parse(TargetPythonVersion.Split('.')[0]) &&
                   version.Minor == int.Parse(TargetPythonVersion.Split('.')[1]);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "检查 Python 版本异常");
            return false;
        }
    }

    /// <summary>
    /// 检查 Pip 是否安装（更可靠的校验逻辑）
    /// </summary>
    public bool CheckPipInstalled()
    {
        try
        {
            logger.LogDebug("检查 Pip 安装状态...");
            var (output, error) = RunPython("-m pip --version");

            // 优先判断错误输出（无 pip 时会有错误信息）
            if (!string.IsNullOrEmpty(error))
            {
                logger.LogDebug("Pip 未安装：{Error}", error);
                return false;
            }

            // 校验输出是否包含 pip 版本特征（更可靠）
            var isInstalled = output.Contains("pip") && output.Contains("from");
            logger.LogDebug("Pip 安装状态：{IsInstalled}，输出：{Output}", isInstalled, output);
            return isInstalled;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "检查 Pip 安装状态异常");
            return false;
        }
    }

    /// <summary>
    /// 检查依赖包（修复原逻辑缺陷，支持版本匹配）
    /// </summary>
    private RequirementCheckResult CheckRequirements()
    {
        var result = new RequirementCheckResult();
        var requirementsPath = GetRequirementsPath();

        try
        {
            logger.LogDebug("检查依赖包：路径={Path}", requirementsPath);

            // 校验依赖文件是否存在
            if (!File.Exists(requirementsPath))
            {
                result.ErrorMessage = $"依赖文件不存在：{requirementsPath}";
                logger.LogError(result.ErrorMessage);
                return result;
            }

            // 解析依赖文件（支持 # 注释、空行、版本约束）
            var requiredPackages = ParseRequirementsFile(requirementsPath);
            if (requiredPackages.Count == 0)
            {
                logger.LogInformation("依赖文件无有效依赖包");
                result.AllSatisfied = true;
                return result;
            }

            // 获取已安装包（通过 pip freeze，更可靠）
            var installedPackages = GetInstalledPackages();
            if (installedPackages.Count == 0)
            {
                result.MissingPackages.AddRange(requiredPackages.Keys);
                logger.LogWarning("未检测到任何已安装的 Python 依赖包");
                return result;
            }

            // 逐个校验依赖
            foreach (var (pkgName, versionSpec) in requiredPackages)
            {
                if (!installedPackages.TryGetValue(pkgName.ToLowerInvariant(), out var installedVersion))
                {
                    result.MissingPackages.Add($"{pkgName}（要求：{versionSpec}）");
                    continue;
                }

                // 无版本约束则直接通过
                if (string.IsNullOrEmpty(versionSpec))
                {
                    logger.LogDebug("依赖包 {PkgName} 已安装（无版本要求）", pkgName);
                    continue;
                }

                // 版本匹配校验
                if (!IsVersionSatisfied(installedVersion, versionSpec))
                {
                    result.VersionMismatchPackages.Add(
                        $"{pkgName}（已安装：{installedVersion}，要求：{versionSpec}）");
                }
            }

            result.AllSatisfied = result.MissingPackages.Count == 0 && result.VersionMismatchPackages.Count == 0;
            return result;
        }
        catch (Exception ex)
        {
            result.ErrorMessage = $"依赖检查异常：{ex.Message}";
            logger.LogError(ex, result.ErrorMessage);
            return result;
        }
    }
    #endregion

    #region 安装与配置方法（优化后）
    /// <summary>
    /// 安装 Pip（支持进度反馈、取消、自动清理）
    /// </summary>
    public async Task<bool> InstallPipAsync(IProgress<DownloadStatus> progress, CancellationToken cancelToken = default)
    {
        var getPipPath = Path.Combine(PathString.PythonDir, GetPipFileName);

        try
        {
            // 1. 下载 get-pip.py（不存在或已损坏时重新下载）
            if (!File.Exists(getPipPath) || new FileInfo(getPipPath).Length == 0)
            {
                logger.LogInformation("下载 get-pip.py：路径={Path}", getPipPath);
                await DownloadUtil.DownloadFileWithDetailsAsync(
                    httpClient, GetPipUrl, getPipPath, progress, cancelToken);
            }

            // 2. 执行 get-pip.py（带取消令牌）
            logger.LogInformation("执行 get-pip.py 安装 Pip...");
            var (output, error) = await RunPythonAsync(getPipPath, cancelToken:cancelToken);

            logger.LogDebug("get-pip.py 输出：{Output}", output);
            logger.LogDebug("get-pip.py 错误输出：{Error}", error);

            // 3. 校验安装结果（双重校验：输出关键字 + 实际检查）
            var installSuccess = output.Contains("Successfully installed pip") && CheckPipInstalled();
            if (installSuccess)
            {
                logger.LogInformation("Pip 安装成功");
                // 清理安装脚本（可选，节省空间）
                if (File.Exists(getPipPath)) File.Delete(getPipPath);
            }
            else
            {
                logger.LogError("Pip 安装失败：{Error}", error);
            }

            return installSuccess;
        }
        catch (OperationCanceledException)
        {
            logger.LogInformation("Pip 安装被取消");
            return false;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Pip 安装异常");
            // 清理无效的安装脚本
            if (File.Exists(getPipPath)) File.Delete(getPipPath);
            return false;
        }
    }

    /// <summary>
    /// 配置 Pip（升级核心工具）
    /// </summary>
    public async Task SetupPipAsync(CancellationToken cancelToken = default)
    {
        logger.LogInformation("升级 pip、setuptools、wheel...");
        await PipInstallAsync("--upgrade pip setuptools wheel", cancelToken);
    }

    /// <summary>
    /// 下载 Python 嵌入式包（带 MD5 校验、断点续传）
    /// </summary>
    public async Task<(string TempZipPath, string ErrorMessage)> DownloadPythonAsync(
        string url, string md5, IProgress<DownloadStatus> progress, CancellationToken cancelToken = default)
    {
        // 临时文件路径（包含版本信息，避免冲突）
        var tempZipPath = Path.Combine(Path.GetTempPath(), $"python-{TargetPythonVersion}-embed-amd64.zip");

        try
        {
            logger.LogInformation("下载 Python 嵌入式包：URL={Url}，临时路径={Path}", url, tempZipPath);

            // 1. 检查本地文件是否已存在且 MD5 匹配
            if (File.Exists(tempZipPath))
            {
                if (DownloadUtil.Md5Check(tempZipPath, md5))
                {
                    logger.LogInformation("本地已存在有效 Python 压缩包，跳过下载");
                    return (tempZipPath, string.Empty);
                }
                logger.LogWarning("本地 Python 压缩包 MD5 不匹配，重新下载");
                File.Delete(tempZipPath);
            }

            // 2. 下载文件（支持断点续传和取消）
            await DownloadUtil.DownloadFileWithDetailsAsync(
                httpClient, url, tempZipPath, progress, cancelToken);

            // 3. MD5 校验
            if (!DownloadUtil.Md5Check(tempZipPath, md5))
            {
                const string errorMsg = "Python 压缩包 MD5 校验失败";
                logger.LogError(errorMsg);
                File.Delete(tempZipPath); // 清理无效文件
                return ("", errorMsg);
            }

            logger.LogInformation("Python 压缩包下载成功：路径={Path}", tempZipPath);
            return (tempZipPath, string.Empty);
        }
        catch (OperationCanceledException)
        {
            const string errorMsg = "Python 下载被取消";
            logger.LogInformation(errorMsg);
            if (File.Exists(tempZipPath)) File.Delete(tempZipPath);
            return ("", errorMsg);
        }
        catch (Exception ex)
        {
            var errorMsg = $"Python 下载失败：{ex.Message}";
            logger.LogError(ex, errorMsg);
            if (File.Exists(tempZipPath)) File.Delete(tempZipPath);
            return ("", errorMsg);
        }
    }

    /// <summary>
    /// 启用 Python site 模块（修改 ._pth 文件）
    /// </summary>
    public void EnableSiteModule()
    {
        var pthFilePath = Path.Combine(PathString.PythonDir, PythonPthFileName);
        const string targetContent = """
                                     python312.zip
                                     .

                                     # Uncomment to run site.main() automatically
                                     import site
                                     """;

        try
        {
            logger.LogInformation("修改 Python ._pth 文件：路径={Path}", pthFilePath);

            // 确保目录存在
            if (!Directory.Exists(PathString.PythonDir))
            {
                Directory.CreateDirectory(PathString.PythonDir);
            }

            // 写入文件（覆盖原有内容）
            File.WriteAllText(pthFilePath, targetContent);
            logger.LogInformation("site 模块启用成功");
        }
        catch (UnauthorizedAccessException ex)
        {
            logger.LogError(ex, "修改 ._pth 文件权限不足，请以管理员身份运行");
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "修改 ._pth 文件异常");
        }
    }

    /// <summary>
    /// 安装依赖包（支持进度反馈、取消、镜像源）
    /// </summary>
    public async Task<bool> InstallRequirementsAsync(IProgress<string> progress, CancellationToken cancelToken = default)
    {
        var requirementsPath = GetRequirementsPath();

        try
        {
            // 校验依赖文件
            if (!File.Exists(requirementsPath))
            {
                logger.LogError("依赖文件不存在：{Path}", requirementsPath);
                progress.Report($"依赖文件不存在：{requirementsPath}");
                return false;
            }

            // 构建 pip 安装命令（支持镜像源）
            var args = $"-r \"{requirementsPath}\"";
            await PipInstallAsync(args, progress, cancelToken);

            // 校验安装结果
            var result = CheckRequirements();
            if (result.AllSatisfied)
            {
                progress.Report("所有依赖包安装成功！");
                logger.LogInformation("依赖包安装完成");
                return true;
            }

            // 反馈安装失败的包
            var errorMsg = $"安装失败：缺失{result.MissingPackages.Count}个包，版本不匹配{result.VersionMismatchPackages.Count}个包";
            progress.Report(errorMsg);
            logger.LogError(errorMsg);
            return false;
        }
        catch (OperationCanceledException)
        {
            progress.Report("依赖包安装被取消");
            logger.LogInformation("依赖包安装被取消");
            return false;
        }
        catch (Exception ex)
        {
            var errorMsg = $"依赖包安装异常：{ex.Message}";
            progress.Report(errorMsg);
            logger.LogError(ex, errorMsg);
            return false;
        }
    }
    #endregion

    #region Pip 安装辅助方法（优化后）
    /// <summary>
    /// 异步执行 Pip 安装（无进度反馈）
    /// </summary>
    private async Task PipInstallAsync(string args, CancellationToken cancelToken = default)
    {
        var fullArgs = BuildPipArgs(args);
        logger.LogInformation("异步执行 Pip 命令：{Args}", fullArgs);
        await RunPythonAsync(fullArgs, 600000, cancelToken);
    }
    /// <summary>
    /// 异步执行 Pip 安装（支持进度反馈和取消）
    /// </summary>
    private async Task PipInstallAsync(string args, IProgress<string> progress, CancellationToken cancelToken = default)
    {
        var fullArgs = BuildPipArgs(args);
        logger.LogInformation("异步执行 Pip 命令：{Args}", fullArgs);
        await RunPythonAsync(fullArgs, progress, 600000, cancelToken);
    }

    /// <summary>
    /// 构建 Pip 命令参数（包含镜像源、信任主机等）
    /// </summary>
    private string BuildPipArgs(string args)
    {
        var baseArgs = "-m pip install --no-warn-script-location "; // 基础参数, 避免脚本位置警告

        // 添加镜像源（支持空值）
        if (!string.IsNullOrEmpty(settingsService.Settings.PipMirror))
            baseArgs += $"-i \"{settingsService.Settings.PipMirror}\" --trusted-host {new Uri(settingsService.Settings.PipMirror).Host} ";

        return baseArgs + args;
    }

    #endregion

    #region Python 进程执行方法（优化后）
    /// <summary>
    /// 同步执行 Python 命令
    /// </summary>
    private (string StdOut, string StdErr) RunPython(string args, int millisecondsTimeout=ProcessExitTimeout)
    {
        using var process = CreatePythonProcess(args);
        try
        {
            process.Start();
            var output = process.StandardOutput.ReadToEnd();
            var error = process.StandardError.ReadToEnd();

            // 等待进程退出（带超时）
            if (process.WaitForExit(millisecondsTimeout)) return (output.Trim(), error.Trim());
            process.Kill(entireProcessTree: true);
            logger.LogWarning("Python 进程超时强制终止：命令={Args}", args);
            return (output, "进程执行超时");

        }
        catch (Exception ex)
        {
            logger.LogError(ex, "同步执行 Python 命令异常：{Args}", args);
            return ("", ex.Message);
        }
    }

    /// <summary>
    /// 异步执行 Python 命令（无进度反馈）
    /// </summary>
    private async Task<(string StdOut, string StdErr)> RunPythonAsync(
        string args,
        int millisecondsTimeout=ProcessExitTimeout,
        CancellationToken cancelToken = default)
    {
        using var process = CreatePythonProcess(args);
        try
        {
            process.Start();

            // 异步读取输出
            var outputTask = process.StandardOutput.ReadToEndAsync(cancelToken);
            var errorTask = process.StandardError.ReadToEndAsync(cancelToken);

            // 等待进程退出（带超时和取消）
            var exitTask = process.WaitForExitAsync(cancelToken);
            var timeoutTask = Task.Delay(millisecondsTimeout, cancelToken);
            var completedTask = await Task.WhenAny(exitTask, timeoutTask);

            if (completedTask == timeoutTask)
            {
                process.Kill(entireProcessTree: true);
                logger.LogWarning("Python 进程超时强制终止：命令={Args}", args);
                return ("", "进程执行超时");
            }

            await Task.WhenAll(outputTask, errorTask);
            return (outputTask.Result.Trim(), errorTask.Result.Trim());
        }
        catch (OperationCanceledException)
        {
            logger.LogInformation("Python 命令执行被取消：{Args}", args);
            return ("", "执行被取消");
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "异步执行 Python 命令异常：{Args}", args);
            return ("", ex.Message);
        }
    }

    /// <summary>
    /// 异步执行 Python 命令（带实时进度反馈）
    /// </summary>
    private async Task RunPythonAsync(string args, IProgress<string> progress, int millisecondsTimeout=ProcessExitTimeout, CancellationToken cancelToken = default)
    {
        using var process = CreatePythonProcess(args);
        try
        {
            // 注册输出事件
            process.OutputDataReceived += (_, e) =>
            {
                if (string.IsNullOrEmpty(e.Data)) return;
                logger.LogDebug("[Python Stdout] {Data}", e.Data);
                progress.Report(e.Data);
            };

            process.ErrorDataReceived += (_, e) =>
            {
                if (string.IsNullOrEmpty(e.Data)) return;
                logger.LogWarning("[Python Stderr] {Data}", e.Data);
                progress.Report($"错误：{e.Data}");
            };

            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();

            // 等待进程退出（带取消）
            var exitTask = process.WaitForExitAsync(cancelToken);
            var timeoutTask = Task.Delay(millisecondsTimeout, cancelToken);
            var completedTask = await Task.WhenAny(exitTask, timeoutTask);

            if (completedTask == timeoutTask)
            {
                process.Kill(entireProcessTree: true);
                logger.LogWarning("Python 进程超时强制终止：命令={Args}", args);
                progress.Report("进程执行超时，已强制终止");
            }
        }
        catch (OperationCanceledException)
        {
            logger.LogInformation("Python 命令执行被取消：{Args}", args);
            progress.Report("执行被取消");
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "异步执行 Python 命令异常：{Args}", args);
            progress.Report($"执行异常：{ex.Message}");
        }
    }

    /// <summary>
    /// 创建 Python 进程配置（统一配置，避免重复）
    /// </summary>
    public Process CreatePythonProcess(string args)
    {
        return new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = PythonExePath,
                Arguments = args,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            },
            EnableRaisingEvents = true
        };
    }
    #endregion

    #region 依赖解析与版本匹配辅助方法
    /// <summary>
    /// 获取依赖文件路径（统一管理）
    /// </summary>
    private string GetRequirementsPath()
    {
        return Path.Combine(PathString.SourceCodeDir, RequirementsFileName);
    }

    /// <summary>
    /// 解析 requirements.txt 文件
    /// </summary>
    private Dictionary<string, string> ParseRequirementsFile(string filePath)
    {
        var packages = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        foreach (var line in File.ReadAllLines(filePath, Encoding.UTF8))
        {
            var trimmedLine = line.Trim();
            // 忽略空行和注释
            if (string.IsNullOrEmpty(trimmedLine) || trimmedLine.StartsWith('#'))
                continue;

            // 解析包名和版本约束（支持 ==、>=、<= 等）
            var versionOperators = new[] { "==", ">=", "<=", ">", "<", "!=" };
            var operatorIndex = -1;
            string? matchedOperator = null;

            foreach (var op in versionOperators)
            {
                operatorIndex = trimmedLine.IndexOf(op, StringComparison.Ordinal);
                if (operatorIndex <= 0) continue;
                matchedOperator = op;
                break;
            }

            if (matchedOperator != null && operatorIndex > 0)
            {
                var pkgName = trimmedLine[..operatorIndex].Trim();
                var versionSpec = trimmedLine[operatorIndex..].Trim();
                if (!string.IsNullOrEmpty(pkgName)) packages.TryAdd(pkgName, versionSpec);
            }
            else
            {
                // 无版本约束
                if (!string.IsNullOrEmpty(trimmedLine) && !packages.ContainsKey(trimmedLine))
                {
                    packages.Add(trimmedLine, string.Empty);
                }
            }
        }

        return packages;
    }

    /// <summary>
    /// 校验版本是否满足约束
    /// </summary>
    private bool IsVersionSatisfied(string installedVersion, string versionSpec)
    {
        try
        {
            // 解析已安装版本（忽略预发布标签，如 rc、beta）
            if (!Version.TryParse(installedVersion.Split('-')[0], out var installedVer))
            {
                logger.LogWarning("无法解析版本号：{Version}", installedVersion);
                return false;
            }

            // 解析版本约束
            string[] versionOperators = ["==", ">=", "<=", ">", "<", "!="];
            string? op = null;
            string? targetVersionStr = null;

            foreach (var possibleOp in versionOperators)
            {
                if (!versionSpec.StartsWith(possibleOp)) continue;
                op = possibleOp;
                targetVersionStr = versionSpec[possibleOp.Length..].Trim();
                break;
            }

            if (op == null || string.IsNullOrEmpty(targetVersionStr) ||
                !Version.TryParse(targetVersionStr.Split('-')[0], out var targetVer))
            {
                logger.LogWarning("无效的版本约束：{Spec}", versionSpec);
                return false;
            }

            // 版本对比
            var compareResult = installedVer.CompareTo(targetVer);
            return op switch
            {
                "==" => compareResult == 0,
                ">=" => compareResult >= 0,
                "<=" => compareResult <= 0,
                ">" => compareResult > 0,
                "<" => compareResult < 0,
                "!=" => compareResult != 0,
                _ => false
            };
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "版本校验异常：已安装={Installed}，约束={Spec}", installedVersion, versionSpec);
            return false;
        }
    }

    /// <summary>
    /// 获取已安装的 Python 包（通过 pip freeze）
    /// </summary>
    private Dictionary<string, string> GetInstalledPackages()
    {
        var installedPackages = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        try
        {
            logger.LogDebug("获取已安装的 Python 包...");
            var (output, error) = RunPython("-m pip freeze --all");

            if (!string.IsNullOrEmpty(error))
            {
                logger.LogWarning("获取已安装包失败：{Error}", error);
                return installedPackages;
            }

            // 解析输出（格式：包名==版本）
            foreach (var line in output.Split('\n', StringSplitOptions.RemoveEmptyEntries))
            {
                var trimmedLine = line.Trim();
                if (trimmedLine.StartsWith("-e")) // 忽略 editable 包
                    continue;

                var parts = trimmedLine.Split(["=="], 2, StringSplitOptions.None);
                if (parts.Length != 2) continue;
                var pkgName = parts[0].Trim();
                var version = parts[1].Trim();
                installedPackages[pkgName.ToLowerInvariant()] = version;
            }

            logger.LogDebug("已检测到 {Count} 个已安装包", installedPackages.Count);
            return installedPackages;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "获取已安装包异常");
            return installedPackages;
        }
    }
    #endregion

    /// <summary>
    /// 依赖包检查结果模型（增强版）
    /// </summary>
    private class RequirementCheckResult
    {
        /// <summary>
        /// 是否所有依赖都满足
        /// </summary>
        public bool AllSatisfied { get; set; }

        /// <summary>
        /// 缺失的依赖包
        /// </summary>
        public List<string> MissingPackages { get; set; } = [];

        /// <summary>
        /// 版本不匹配的依赖包
        /// </summary>
        public List<string> VersionMismatchPackages { get; set; } = [];

        /// <summary>
        /// 错误信息
        /// </summary>
        public string ErrorMessage { get; set; } = string.Empty;
    }
}
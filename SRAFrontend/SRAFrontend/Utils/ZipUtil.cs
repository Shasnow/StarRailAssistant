using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;

namespace SRAFrontend.Utils;

/// <summary>资源完整性校验结果</summary>
/// <param name="TotalCount">清单中的文件总数</param>
/// <param name="MissingFiles">缺失文件的相对路径列表</param>
/// <param name="CorruptedFiles">MD5 不匹配（损坏或版本不一致）的文件相对路径列表</param>
public sealed record IntegrityCheckResult(
    int TotalCount,
    IReadOnlyList<string> MissingFiles,
    IReadOnlyList<string> CorruptedFiles)
{
    /// <summary>全部文件是否完整</summary>
    public bool IsIntact => MissingFiles.Count == 0 && CorruptedFiles.Count == 0;
}

/// <summary>冗余文件信息（应用目录下不在 MD5 清单中的文件）</summary>
/// <param name="RelativePath">相对于应用根目录的路径（正斜杠分隔）</param>
/// <param name="Size">文件大小（字节）</param>
public sealed record RedundantFileInfo(string RelativePath, long Size);

public static class ZipUtil
{
    /// <summary>
    /// MD5 完整性清单在应用目录（以及安装包内）的固定文件名，由打包脚本 package.py 写入压缩包根部
    /// </summary>
    public const string ManifestFileName = "manifest.md5.json";

    /// <summary>
    /// 根据 MD5 清单（manifest.md5.json）校验指定目录的资源完整性
    /// </summary>
    /// <param name="baseDir">应用根目录，清单中的相对路径基于此目录解析</param>
    /// <returns>校验结果：缺失与不匹配的文件列表</returns>
    /// <exception cref="FileNotFoundException">清单文件不存在（可能未经应用内更新安装）时抛出</exception>
    /// <exception cref="InvalidDataException">清单文件不是合法 JSON 时抛出</exception>
    public static IntegrityCheckResult CheckIntegrity(string baseDir)
    {
        var manifest = LoadManifest(baseDir);
        var missing = new List<string>();
        var corrupted = new List<string>();
        foreach (var (relativePath, expectedMd5) in manifest)
        {
            var filePath = Path.Combine(baseDir, relativePath);
            if (!File.Exists(filePath))
            {
                missing.Add(relativePath);
                continue;
            }
            // MD5 不匹配视为文件损坏或版本不一致
            if (CalculateFileMd5(filePath) != expectedMd5) corrupted.Add(relativePath);
        }
        return new IntegrityCheckResult(manifest.Count, missing, corrupted);
    }

    /// <summary>
    /// 扫描应用目录下所有不在 MD5 清单中的冗余文件（更新残留、日志等非安装内容）
    /// </summary>
    /// <param name="baseDir">应用根目录</param>
    /// <returns>冗余文件列表（按相对路径排序）</returns>
    /// <exception cref="FileNotFoundException">清单文件不存在时抛出</exception>
    /// <exception cref="InvalidDataException">清单文件不是合法 JSON 时抛出</exception>
    public static IReadOnlyList<RedundantFileInfo> ScanRedundantFiles(string baseDir)
    {
        var manifest = LoadManifest(baseDir);
        var redundant = new List<RedundantFileInfo>();
        foreach (var filePath in Directory.EnumerateFiles(baseDir, "*", SearchOption.AllDirectories))
        {
            var relativePath = Path.GetRelativePath(baseDir, filePath).Replace('\\', '/');
            if (relativePath == ManifestFileName || manifest.ContainsKey(relativePath)) continue;
            redundant.Add(new RedundantFileInfo(relativePath, new FileInfo(filePath).Length));
        }
        return [.. redundant.OrderBy(f => f.RelativePath)];
    }

    /// <summary>
    /// 删除指定的冗余文件，并清理因此变空的目录
    /// </summary>
    /// <param name="baseDir">应用根目录</param>
    /// <param name="relativePaths">要删除的文件相对路径列表（正斜杠分隔）</param>
    /// <returns>成功删除的文件数、释放的字节数与删除失败（可能被占用）的文件列表</returns>
    public static (int DeletedCount, long FreedBytes, IReadOnlyList<string> FailedFiles) DeleteFiles(
        string baseDir, IEnumerable<string> relativePaths)
    {
        var deletedCount = 0;
        long freedBytes = 0;
        var failed = new List<string>();
        foreach (var relativePath in relativePaths)
        {
            var filePath = Path.Combine(baseDir, relativePath);
            try
            {
                var size = new FileInfo(filePath).Length;
                File.Delete(filePath);
                deletedCount++;
                freedBytes += size;
            }
            catch (Exception)
            {
                failed.Add(relativePath);
            }
        }
        // 自底向上清理删除后变空的目录（忽略失败）
        foreach (var dir in Directory.EnumerateDirectories(baseDir, "*", SearchOption.AllDirectories)
                     .OrderByDescending(d => d.Length).ToList())
        {
            try
            {
                if (!Directory.EnumerateFileSystemEntries(dir).Any()) Directory.Delete(dir);
            }
            catch (Exception)
            {
                // 目录被占用或非空，跳过
            }
        }
        return (deletedCount, freedBytes, failed);
    }

    /// <summary>把字节数格式化为人类可读的大小文本（B/KB/MB/GB/TB）</summary>
    public static string FormatFileSize(long bytes)
    {
        const long scale = 1024;
        if (bytes < scale) return $"{bytes} B";
        double value = bytes;
        foreach (var unit in new[] { "KB", "MB", "GB" })
        {
            value /= scale;
            if (value < scale) return $"{value:0.##} {unit}";
        }
        return $"{value:0.##} TB";
    }

    /// <summary>读取应用目录下的 MD5 完整性清单</summary>
    /// <exception cref="FileNotFoundException">清单文件不存在时抛出</exception>
    /// <exception cref="InvalidDataException">清单文件不是合法 JSON 时抛出</exception>
    private static Dictionary<string, string> LoadManifest(string baseDir)
    {
        var manifestPath = Path.Combine(baseDir, ManifestFileName);
        if (!File.Exists(manifestPath)) throw new FileNotFoundException("未找到 MD5 完整性清单", manifestPath);
        var manifest = JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(manifestPath));
        if (manifest is null || manifest.Count == 0) throw new InvalidDataException("MD5 清单内容为空或格式错误");
        return manifest;
    }

    /// <summary>
    /// 使用外部工具 - 系统自带的tar命令解压tar文件
    /// </summary>
    /// <param name="path">压缩包路径</param>
    /// <param name="target">目标路径</param>
    public static void UnzipExternal(string path, string target)
    {
        Process.Start(new ProcessStartInfo
        {
            FileName = "cmd.exe",
            Arguments = $"/C tar -xf \"{path}\" -C \"{target}\"",
            UseShellExecute = false
        });
    }

    /// <summary>
    /// 解压ZIP文件，跳过目标目录中已存在且MD5相同的文件
    /// </summary>
    /// <param name="zipFilePath">ZIP文件路径</param>
    /// <param name="targetDir">目标解压目录</param>
    /// <exception cref="FileNotFoundException">ZIP文件不存在时抛出</exception>
    /// <exception cref="IOException">IO操作失败时抛出</exception>
    public static void Unzip(string zipFilePath, string targetDir)
    {
        // 基础校验：确保ZIP文件存在
        if (!File.Exists(zipFilePath)) throw new FileNotFoundException("ZIP文件不存在", zipFilePath);
        // 确保目标目录存在
        Directory.CreateDirectory(targetDir);
        // 生成临时解压目录（避免与现有文件冲突）
        var tempDir = Path.Combine(Path.GetTempPath(), Path.GetRandomFileName());
        try
        {
            Directory.CreateDirectory(tempDir);
            // 第一步：解压ZIP到临时目录
            ZipFile.ExtractToDirectory(zipFilePath, tempDir);
            // 第二步：遍历临时目录所有目录，先创建目标目录结构（避免文件拷贝时目录不存在）
            foreach (var dirPath in Directory.GetDirectories(tempDir, "*", SearchOption.AllDirectories))
            {
                var targetDirPath = dirPath.Replace(tempDir, targetDir);
                if (!Directory.Exists(targetDirPath)) Directory.CreateDirectory(targetDirPath);
            }
            // 第三步：遍历所有文件，MD5校验后选择性拷贝
            foreach (var tempFilePath in Directory.GetFiles(tempDir, "*.*", SearchOption.AllDirectories))
            {
                // 计算临时文件的MD5
                var tempFileMd5 = CalculateFileMd5(tempFilePath);
                if (string.IsNullOrEmpty(tempFileMd5)) continue; // MD5计算失败，跳过该文件
                // 转换为目标文件路径
                var targetFilePath = tempFilePath.Replace(tempDir, targetDir);
                // 检查目标文件是否存在：不存在则直接拷贝；存在则校验MD5
                if (!File.Exists(targetFilePath)) File.Copy(tempFilePath, targetFilePath, true);
                else
                {
                    // 计算目标文件的MD5
                    var targetFileMd5 = CalculateFileMd5(targetFilePath);
                    // 仅当MD5不同时才覆盖拷贝
                    if (tempFileMd5 != targetFileMd5) File.Copy(tempFilePath, targetFilePath, true);
                    // MD5相同则跳过，无需操作
                }
            }
        }
        finally
        {
            // 最终确保临时目录被删除（即使中间出现异常）
            if (Directory.Exists(tempDir)) Directory.Delete(tempDir, true);
        }
    }

    /// <summary>
    /// 计算文件的MD5哈希值（小写32位）
    /// </summary>
    /// <param name="filePath">文件路径</param>
    /// <returns>MD5字符串（失败返回空）</returns>
    private static string CalculateFileMd5(string filePath)
    {
        try
        {
            using var md5 = MD5.Create();
            using var stream = File.OpenRead(filePath);
            var hashBytes = md5.ComputeHash(stream);
            // 转换为小写32位MD5字符串
            return BitConverter.ToString(hashBytes).Replace("-", "").ToLowerInvariant();
        }
        catch (Exception)
        {
            return string.Empty;
        }
    }
}
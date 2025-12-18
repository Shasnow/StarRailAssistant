using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;

namespace SRAFrontend.utilities;

public static class ZipUtil
{
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
            CreateNoWindow = true,
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
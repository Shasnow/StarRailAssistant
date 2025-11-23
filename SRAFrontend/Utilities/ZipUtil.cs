using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Threading;
using System.Threading.Tasks;

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
    /// 使用内置方法解压zip文件
    /// </summary>
    /// <param name="path">源归档文件路径</param>
    /// <param name="target">目的地目录</param>
    public static void Unzip(string path, string target)
    {
        // 确保目标目录存在，覆盖已存在的文件
        Directory.CreateDirectory(target);
        ZipFile.ExtractToDirectory(path, target, overwriteFiles: true);
    }
}
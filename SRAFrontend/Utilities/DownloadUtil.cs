using System;
using System.IO;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

namespace SRAFrontend.utilities;

public static class DownloadUtil
{
    /// <summary>
    /// 下载文件并提供详细的下载状态回调
    /// </summary>
    /// <param name="httpClient">httpclient</param>
    /// <param name="url">下载url</param>
    /// <param name="savePath">保存路径</param>
    /// <param name="statusProgress">状态回调</param>
    /// <param name="cancellationToken">取消下载token</param>
    public static async Task DownloadFileWithDetailsAsync(
        HttpClient httpClient,
        string url,
        string savePath,
        IProgress<DownloadStatus> statusProgress,
        CancellationToken cancellationToken)
    {
        using var response = await httpClient.GetAsync(
            url,
            HttpCompletionOption.ResponseHeadersRead,
            cancellationToken);
        response.EnsureSuccessStatusCode();

        // 获取文件总大小（回调给UI）
        var totalBytes = response.Content.Headers.ContentLength ?? 0;
        long downloadedBytes = 0;
        var buffer = new byte[8192]; // 8KB缓冲区

        // 速度计算相关变量
        var lastUpdateTime = DateTime.UtcNow;
        long bytesSinceLastUpdate = 0;
        double currentSpeed = 0;

        await using (var responseStream = await response.Content.ReadAsStreamAsync(cancellationToken))
        await using (var fileStream = new FileStream(
                         savePath, 
                         FileMode.Create,
                         FileAccess.Write,
                         FileShare.None,
                         buffer.Length,
                         true))
        {
            int bytesRead;
            while ((bytesRead = await responseStream.ReadAsync(buffer, cancellationToken)) > 0)
            {
                // 写入文件
                await fileStream.WriteAsync(buffer.AsMemory(0, bytesRead), cancellationToken);

                // 更新已下载字节数
                downloadedBytes += bytesRead;
                bytesSinceLastUpdate += bytesRead;

                // 计算下载速度（每500ms更新一次）
                var now = DateTime.UtcNow;
                var elapsed = now - lastUpdateTime;
                if (elapsed.TotalMilliseconds >= 500)
                {
                    currentSpeed = bytesSinceLastUpdate / elapsed.TotalSeconds;
                    lastUpdateTime = now;
                    bytesSinceLastUpdate = 0;
                }

                // 构建状态信息并回调
                var status = new DownloadStatus
                {
                    TotalBytes = totalBytes,
                    DownloadedBytes = downloadedBytes,
                    BytesPerSecond = currentSpeed,
                    ProgressPercent = totalBytes > 0
                        ? (float)downloadedBytes / totalBytes * 100
                        : -0.5f // 无法获取总大小时的标记
                };
                statusProgress.Report(status);
            }
        }

        // 下载完成，确保最终状态正确
        statusProgress.Report(new DownloadStatus
        {
            TotalBytes = totalBytes,
            DownloadedBytes = totalBytes,
            BytesPerSecond = 0,
            ProgressPercent = 100
        });
    }
    
    public static bool Md5Check(string filePath, string expectedMd5)
    {
        using var md5 = System.Security.Cryptography.MD5.Create();
        using var stream = File.OpenRead(filePath);
        var hash = md5.ComputeHash(stream);
        var fileMd5 = BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
        return fileMd5.Equals(expectedMd5, StringComparison.InvariantCultureIgnoreCase);
    }
}

/// <summary>
///     下载状态信息（用于回调）
/// </summary>
public class DownloadStatus
{
    /// <summary>当前下载进度（0-100）</summary>
    public float ProgressPercent { get; init; }

    /// <summary>文件总大小（字节）</summary>
    public long TotalBytes { get; init; }

    /// <summary>已下载字节数</summary>
    public long DownloadedBytes { get; init; }

    /// <summary>当前下载速度（字节/秒）</summary>
    public double BytesPerSecond { get; init; }

    /// <summary>速度格式化显示（如 "1.2 MB/s"）</summary>
    public string FormattedSpeed => FormatSpeed(BytesPerSecond);

    /// <summary>总大小格式化显示（如 "2.5 GB"）</summary>
    public string FormattedTotalSize => FormatSize(TotalBytes);

    /// <summary>已下载大小格式化显示</summary>
    public string FormattedDownloadedSize => FormatSize(DownloadedBytes);

    // 辅助方法：格式化文件大小（B/KB/MB/GB）
    private static string FormatSize(long bytes)
    {
        return bytes switch
        {
            < 1024 => $"{bytes} B",
            < 1024 * 1024 => $"{bytes / 1024.0:F1} KB",
            < 1024 * 1024 * 1024 => $"{bytes / (1024.0 * 1024):F1} MB",
            _ => $"{bytes / (1024.0 * 1024 * 1024):F1} GB"
        };
    }

    // 辅助方法：格式化速度（B/s/KB/s/MB/s）
    private static string FormatSpeed(double bytesPerSecond)
    {
        return bytesPerSecond switch
        {
            < 1024 => $"{bytesPerSecond:F0} B/s",
            < 1024 * 1024 => $"{bytesPerSecond / 1024:F1} KB/s",
            _ => $"{bytesPerSecond / (1024 * 1024):F1} MB/s"
        };
    }
}
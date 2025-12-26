using System;
using System.IO;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

namespace SRAFrontend.utilities;

public static class DownloadUtil
{
    /// <summary>
    /// 并发分段下载，支持断点续传。服务器需支持 Range（Accept-Ranges: bytes），否则回退为单线程下载。
    /// </summary>
    /// <param name="httpClient">HTTP 客户端</param>
    /// <param name="url">下载地址</param>
    /// <param name="savePath">保存路径（最终合并后的文件）</param>
    /// <param name="statusProgress">下载状态回调</param>
    /// <param name="cancellationToken">取消 Token</param>
    /// <param name="maxConcurrency">最大并发分段数</param>
    /// <param name="segmentSizeBytes">每段大小（字节）</param>
    public static async Task DownloadFileSegmentedWithResumeAsync(
        HttpClient httpClient,
        string url,
        string savePath,
        IProgress<DownloadStatus> statusProgress,
        CancellationToken cancellationToken,
        int maxConcurrency = 8,
        long segmentSizeBytes = 4 * 1024 * 1024)
    {
        // 预检：获取头部，判断是否支持 Range
        long totalBytes = 0;
        var supportsRange = false;
        try
        {
            using var headReq = new HttpRequestMessage(HttpMethod.Head, url);
            using var headResp = await httpClient.SendAsync(headReq, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
            if (headResp.IsSuccessStatusCode)
            {
                totalBytes = headResp.Content.Headers.ContentLength ?? 0;
                var acceptRanges = headResp.Headers.TryGetValues("Accept-Ranges", out var ar) ? string.Join(",", ar) : string.Empty;
                supportsRange = acceptRanges.Contains("bytes", StringComparison.OrdinalIgnoreCase) && totalBytes > 0;
            }
        }
        catch
        {
            // 某些服务不支持 HEAD，忽略错误，稍后用 GET 再试
        }

        if (!supportsRange)
        {
            // 尝试用 GET 仅获取头信息
            using var resp = await httpClient.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
            resp.EnsureSuccessStatusCode();
            totalBytes = resp.Content.Headers.ContentLength ?? 0;
            var acceptRanges = resp.Headers.TryGetValues("Accept-Ranges", out var ar2) ? string.Join(",", ar2) : string.Empty;
            supportsRange = acceptRanges.Contains("bytes", StringComparison.OrdinalIgnoreCase) && totalBytes > 0;
            // 若不支持 Range 或无法获取总大小，回退为单线程下载
            if (!supportsRange || totalBytes <= 0)
            {
                await DownloadFileWithDetailsAsync(httpClient, url, savePath, statusProgress, cancellationToken);
                return;
            }
        }

        // 计算分段
        if (segmentSizeBytes <= 0) segmentSizeBytes = 4 * 1024 * 1024;
        if (maxConcurrency <= 0) maxConcurrency = 1;
        var segmentCount = (int)((totalBytes + segmentSizeBytes - 1) / segmentSizeBytes);
        var partDir = Path.GetDirectoryName(savePath)!;
        Directory.CreateDirectory(partDir);
        var baseName = Path.GetFileName(savePath);

        // 进度与速度统计
        long downloadedBytes = 0; // 合计已下载（含已存在分段）
        var lastUpdateTime = DateTime.UtcNow;
        long bytesSinceLastUpdate = 0;
        double currentSpeed = 0;

        // 统计已存在的分段文件以实现断点续传
        var segmentInfos = new (long start, long end, string partPath)[segmentCount];
        for (var i = 0; i < segmentCount; i++)
        {
            var start = i * segmentSizeBytes;
            var end = Math.Min(start + segmentSizeBytes - 1, totalBytes - 1);
            var partPath = Path.Combine(partDir, baseName + $".part{i}");
            segmentInfos[i] = (start, end, partPath);

            if (File.Exists(partPath))
            {
                var len = new FileInfo(partPath).Length;
                var expected = end - start + 1;
                if (len > 0)
                {
                    // 如果已有分段的大小不超过预期，则计入已下载字节
                    downloadedBytes += Math.Min(len, expected);
                }
            }
        }

        // 初始状态回调
        statusProgress.Report(new DownloadStatus
        {
            TotalBytes = totalBytes,
            DownloadedBytes = downloadedBytes,
            BytesPerSecond = 0,
            ProgressPercent = totalBytes > 0 ? (float)downloadedBytes / totalBytes * 100 : -0.5f
        });

        // 并发下载剩余分段
        using var semaphore = new SemaphoreSlim(maxConcurrency);
        var tasks = new Task[segmentCount];
        for (var i = 0; i < segmentCount; i++)
        {
            var (start, end, partPath) = segmentInfos[i];
            var expectedLength = end - start + 1;
            var existingLength = File.Exists(partPath) ? new FileInfo(partPath).Length : 0;
            if (existingLength >= expectedLength)
            {
                // 已完成分段，跳过
                tasks[i] = Task.CompletedTask;
                continue;
            }

            tasks[i] = Task.Run(async () =>
            {
                await semaphore.WaitAsync(cancellationToken);
                try
                {
                    var rangeStart = start + existingLength;
                    if (rangeStart > end) return; // 已完成

                    using var req = new HttpRequestMessage(HttpMethod.Get, url);
                    req.Headers.Range = new System.Net.Http.Headers.RangeHeaderValue(rangeStart, end);
                    using var resp = await httpClient.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
                    resp.EnsureSuccessStatusCode();

                    await using var respStream = await resp.Content.ReadAsStreamAsync(cancellationToken);
                    // 以追加模式写入分段文件
                    await using var fs = new FileStream(partPath, FileMode.Append, FileAccess.Write, FileShare.None, 8192, true);
                    var buffer = new byte[8192];
                    int read;
                    while ((read = await respStream.ReadAsync(buffer.AsMemory(0, buffer.Length), cancellationToken)) > 0)
                    {
                        await fs.WriteAsync(buffer.AsMemory(0, read), cancellationToken);
                        Interlocked.Add(ref downloadedBytes, read);
                        bytesSinceLastUpdate += read;

                        // 速度每500ms更新一次
                        var now = DateTime.UtcNow;
                        var elapsed = now - lastUpdateTime;
                        if (elapsed.TotalMilliseconds >= 500)
                        {
                            currentSpeed = bytesSinceLastUpdate / elapsed.TotalSeconds;
                            lastUpdateTime = now;
                            bytesSinceLastUpdate = 0;
                        }

                        statusProgress.Report(new DownloadStatus
                        {
                            TotalBytes = totalBytes,
                            DownloadedBytes = Interlocked.Read(ref downloadedBytes),
                            BytesPerSecond = currentSpeed,
                            ProgressPercent = totalBytes > 0 ? (float)Interlocked.Read(ref downloadedBytes) / totalBytes * 100 : -0.5f
                        });
                    }
                }
                finally
                {
                    semaphore.Release();
                }
            }, cancellationToken);
        }

        await Task.WhenAll(tasks);

        // 合并分段为最终文件
        await using (var outFs = new FileStream(savePath, FileMode.Create, FileAccess.Write, FileShare.None, 8192, true))
        {
            for (var i = 0; i < segmentCount; i++)
            {
                var partPath = segmentInfos[i].partPath;
                var exists = File.Exists(partPath);
                if (!exists) continue; // 理论上不应发生
                await using var inFs = new FileStream(partPath, FileMode.Open, FileAccess.Read, FileShare.Read, 8192, true);
                await inFs.CopyToAsync(outFs, 8192, cancellationToken);
            }
        }

        // 清理分段文件
        for (var i = 0; i < segmentCount; i++)
        {
            var partPath = segmentInfos[i].partPath;
            if (File.Exists(partPath))
            {
                try { File.Delete(partPath); } catch { /* 忽略 */ }
            }
        }

        // 完成状态
        statusProgress.Report(new DownloadStatus
        {
            TotalBytes = totalBytes,
            DownloadedBytes = totalBytes,
            BytesPerSecond = 0,
            ProgressPercent = 100
        });
    }

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
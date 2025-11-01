using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class UpdateService(HttpClient httpClient, ILogger<UpdateService> logger)
{
    private const string BaseVersionUrl =
        "https://mirrorchyan.com/api/resources/StarRailAssistant/latest";

    private const string BaseDownloadUrl =
        "https://github.com/Shasnow/StarRailAssistant/releases/download/{version}/StarRailAssistant_{version}.zip";

    private readonly Dictionary<int, string> _errorCodes = new()
    {
        { 1001, "获取版本信息的URL参数不正确" },
        { 7001, "填入的 CDK 已过期" },
        { 7002, "填入的 CDK 错误" },
        { 7003, "填入的 CDK 今日下载次数已达上限" },
        { 7004, "填入的 CDK 类型和待下载的资源不匹配" },
        { 7005, "填入的 CDK 已被封禁" },
        { 8001, "对应架构和系统下的资源不存在" },
        { 8002, "错误的系统参数" },
        { 8003, "错误的架构参数" },
        { 8004, "错误的更新通道参数" }
    };

    public async Task<VersionResponse?> VerifyCdkAsync(string cdk)
    {
        // Simulate a call to an external service to verify the CDK
        var response = await httpClient.GetAsync($"{BaseVersionUrl}?cdk={cdk}");
        return await response.Content.ReadFromJsonAsync<VersionResponse>();
    }

    public string GetErrorMessage(int code)
    {
        return _errorCodes.GetValueOrDefault(code, "未知错误");
    }

    public async Task<VersionResponse?> CheckForUpdatesAsync(string? currentVersion = null, string? cdk = null,
        string? channel = null)
    {
        var url = BaseVersionUrl;
        var queryParams = new List<string>();
        if (!string.IsNullOrEmpty(currentVersion))
            queryParams.Add($"current_version={currentVersion}");
        if (!string.IsNullOrEmpty(cdk))
            queryParams.Add($"cdk={cdk}");
        if (!string.IsNullOrEmpty(channel))
            queryParams.Add($"channel={channel}");
        if (queryParams.Count > 0)
            url += "?user_agent=SRA_avalonia" + string.Join("&", queryParams);

        var response = await httpClient.GetAsync(url);
        return await response.Content.ReadFromJsonAsync<VersionResponse>();
    }

    public async Task<string> DownloadUpdateAsync(
        VersionResponse versionResponse,
        int downloadChannel,
        IProgress<DownloadStatus> statusProgress,
        IEnumerable<string>? proxies = null,
        CancellationToken cancellationToken = default
    )
    {
        // 确定下载URL和保存路径
        var downloadUrl = GetDownloadUrl(versionResponse, downloadChannel);
        if (string.IsNullOrEmpty(downloadUrl))
            throw new InvalidOperationException("无法获取有效的下载地址");

        var saveFileName = $"update_{versionResponse.Data.VersionName}.zip";
        var savePath = Path.Combine(
            Path.GetTempPath(),
            "SRA",
            saveFileName
        );
        Directory.CreateDirectory(Path.GetDirectoryName(savePath)!);

        // 下载候选地址（代理+直连）
        var downloadCandidates = new List<string>();
        if (downloadChannel==1)
        {
            if (proxies is not null)
                downloadCandidates.AddRange(proxies.Select(proxy =>
                    $"{proxy.TrimEnd('/')}/{downloadUrl.TrimStart('/')}"));
        }
        downloadCandidates.Add(downloadUrl);

        // 尝试下载
        var downloadSuccess = false;
        Exception? lastException = null;
        foreach (var candidateUrl in downloadCandidates)
            try
            {
                logger.LogDebug("尝试从 {Url} 下载更新", candidateUrl);
                await DownloadFileWithDetailsAsync(
                    candidateUrl,
                    savePath,
                    statusProgress,
                    cancellationToken
                );
                downloadSuccess = true;
                break;
            }
            catch (Exception ex)
            {
                lastException = ex;
                statusProgress.Report(new DownloadStatus { ProgressPercent = -1 }); // 代理失败标记
                await Task.Delay(1000, cancellationToken);
            }

        if (downloadSuccess) return savePath;
        
        if (File.Exists(savePath)) File.Delete(savePath);
        throw lastException ?? new InvalidOperationException("所有下载方式均失败");

    }

    // 核心下载逻辑（包含大小和速度计算）
    private async Task DownloadFileWithDetailsAsync(
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

    // 辅助方法：获取下载URL
    private string GetDownloadUrl(VersionResponse versionResponse, int downloadChannel)
    {
        if (versionResponse.Data.Url == "" || downloadChannel==1)
            return BaseDownloadUrl.Replace("{version}", versionResponse.Data.VersionName);
        return versionResponse.Data.Url;
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
using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Utils;

namespace SRAFrontend.Services;

public class UpdateService(IHttpClientFactory httpClientFactory, ILogger<UpdateService> logger)
{
    private const string BaseVersionUrl =
        "https://mirrorchyan.com/api/resources/StarRailAssistant/latest";

    private const string BaseDownloadUrl =
        "https://github.com/Shasnow/StarRailAssistant/releases/download/{version}/StarRailAssistant_{version}.zip";

    private const string BaseDownloadUrl2 =
        "https://download.auto-mas.top/d/StarRailAssistant/StarRailAssistant-{version}.zip";

    private const string BaseSha256Url =
        "https://download.auto-mas.top/d/StarRailAssistant/StarRailAssistant-{version}.sha256";

    private const string BaseCoreDownloadUrl =
        "https://download.auto-mas.top/d/StarRailAssistant/StarRailAssistant_Core_{version}.zip";

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
        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        var response = await httpClient.GetAsync($"{BaseVersionUrl}?cdk={cdk}");
        return await response.Content.ReadFromJsonAsync<VersionResponse>();
    }

    public string GetErrorMessage(int code)
    {
        return _errorCodes.GetValueOrDefault(code, "Unknown error code.");
    }

    public async Task<VersionResponse?> GetRemoteVersionAsync(string? currentVersion = null, string? cdk = null,
        string? channel = null)
    {
        var url = BaseVersionUrl;
        var queryParams = new List<string>();
        if (!string.IsNullOrEmpty(currentVersion))
            queryParams.Add($"current_version=v{currentVersion}");
        if (!string.IsNullOrEmpty(cdk))
            queryParams.Add($"cdk={cdk}");
        if (!string.IsNullOrEmpty(channel))
            queryParams.Add($"channel={channel}");
        if (queryParams.Count > 0)
            url += "?user_agent=SRA" + string.Join("&", queryParams);

        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        try
        {
            var response = await httpClient.GetAsync(url);
            return await response.Content.ReadFromJsonAsync<VersionResponse>();
        }
        catch (Exception)
        {
            return null;
        }
    }

    /// <summary>
    ///     异步下载更新包
    /// </summary>
    /// <param name="versionResponse">版本响应模型</param>
    /// <param name="downloadChannel">下载渠道</param>
    /// <param name="statusProgress">下载状态回调</param>
    /// <param name="cancellationToken">取消下载Token</param>
    /// <returns>更新文件的路径</returns>
    /// <exception cref="Exception"></exception>
    public async Task<string> DownloadUpdateAsync(
        VersionResponse versionResponse,
        int downloadChannel,
        IProgress<DownloadStatus> statusProgress,
        CancellationToken cancellationToken = default
    )
    {
        var version = versionResponse.Data.VersionName;
        var downloadUrl = GetDownloadUrl(versionResponse, downloadChannel);
        var sha256 = await GetSha256Async(versionResponse, cancellationToken);

        var saveFileName = $"update_{version}.zip";
        var savePath = Path.Combine(PathString.TempDir, saveFileName);
        Directory.CreateDirectory(Path.GetDirectoryName(savePath)!);

        // 1. 如果已有文件，则先校验
        if (File.Exists(savePath))
        {
            logger.LogInformation("Found existing update file, verifying SHA256: {Path}", savePath);
            if (await VerifyFileSha256Async(savePath, sha256, cancellationToken))
            {
                logger.LogInformation("Existing update file passed SHA256 verification, reuse it.");
                return savePath;
            }

            logger.LogWarning("Existing update file failed SHA256 verification, deleting: {Path}", savePath);
            File.Delete(savePath);
        }

        // 2. 下载文件
        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        logger.LogDebug("Downloading update");
        await DownloadUtil.DownloadFileWithDetailsAsync(
            httpClient,
            downloadUrl,
            savePath,
            statusProgress,
            cancellationToken
        );

        // 3. 下载后再校验一次
        if (!await VerifyFileSha256Async(savePath, sha256, cancellationToken))
        {
            File.Delete(savePath);
            throw new InvalidOperationException("Downloaded update file failed SHA256 verification.");
        }

        return savePath;
    }

    /// <summary>
    ///     异步下载热更新包，并在下载后进行 SHA256 校验（沿用主程序的 .sha256）。
    /// </summary>
    public async Task<string> DownloadHotfixAsync(
        VersionResponse versionResponse,
        IProgress<DownloadStatus> statusProgress,
        CancellationToken cancellationToken = default
    )
    {
        var hotfixVersion = versionResponse.Data.VersionName;
        var downloadUrl = BaseCoreDownloadUrl.Replace("{version}", hotfixVersion);
        logger.LogDebug("Downloading hotfix from URL: {Url}", downloadUrl);
        var saveFileName = $"core_update_{hotfixVersion}.zip";
        var savePath = Path.Combine(PathString.TempDir, saveFileName);
        Directory.CreateDirectory(Path.GetDirectoryName(savePath)!);

        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        await DownloadUtil.DownloadFileWithDetailsAsync(
            httpClient,
            downloadUrl,
            savePath,
            statusProgress,
            cancellationToken
        );

        // 使用主程序的 sha256 校验热更包的一致性（如果服务端有单独的校验地址，可再扩展）
        var sha256 = await GetSha256Async(versionResponse, cancellationToken);
        if (!await VerifyFileSha256Async(savePath, sha256, cancellationToken))
        {
            File.Delete(savePath);
            throw new InvalidOperationException("Downloaded hotfix file failed SHA256 verification.");
        }

        return savePath;
    }

    // 辅助方法：获取下载URL
    private string GetDownloadUrl(VersionResponse versionResponse, int downloadChannel)
    {
        if (versionResponse.Data.Url == "" || downloadChannel == 2)
            return BaseDownloadUrl2.Replace("{version}", versionResponse.Data.VersionName);
        if (downloadChannel == 1)
            return BaseDownloadUrl.Replace("{version}", versionResponse.Data.VersionName);
        return versionResponse.Data.Url;
    }

    /// <summary>
    ///     获取指定版本的 SHA256 字符串。
    /// </summary>
    private async Task<string> GetSha256Async(VersionResponse versionResponse, CancellationToken cancellationToken)
    {
        if (!string.IsNullOrEmpty(versionResponse.Data.Sha256))
            return versionResponse.Data.Sha256;
        var url = BaseSha256Url.Replace("{version}", versionResponse.Data.VersionName);
        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        logger.LogDebug("Fetching SHA256");
        var response = await httpClient.GetAsync(url, cancellationToken);
        response.EnsureSuccessStatusCode();
        var content = await response.Content.ReadAsStringAsync(cancellationToken);

        // 服务器返回为纯哈希字符串，去掉首尾空白即可
        return content.Trim().ToLowerInvariant();
    }

    /// <summary>
    ///     校验本地文件的 SHA256 是否与远端一致。
    /// </summary>
    private static async Task<bool> VerifyFileSha256Async(string filePath, string expectedSha256,
        CancellationToken cancellationToken)
    {
        if (!File.Exists(filePath)) return false;
        if (string.IsNullOrEmpty(expectedSha256)) return true;

        await using var stream = File.OpenRead(filePath);
        using var sha256 = SHA256.Create();
        var hash = await sha256.ComputeHashAsync(stream, cancellationToken);
        var sb = new StringBuilder(hash.Length * 2);
        foreach (var b in hash)
            sb.Append(b.ToString("x2"));
        var actual = sb.ToString().ToLowerInvariant();
        return string.Equals(actual, expectedSha256, StringComparison.OrdinalIgnoreCase);
    }
}
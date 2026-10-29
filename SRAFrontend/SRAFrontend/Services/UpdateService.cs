using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
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

    private const string DataCenterReleaseMetadataUrl =
        "https://data.auto-mas.top/api/v1/files/starrailassistant/Release/{channel}";

    private const string GitHubReleaseMetadataUrl =
        "https://api.github.com/repos/Shasnow/StarRailAssistant/releases/tags/{version}";

    // 数据中心目前没有热更包（Core）产物：旧站 download.auto-mas.top 上该资源已长期未上传
    // （实测返回 500 object not found），客户端侧 DownloadHotfixAsync 也因 isHotfix 恒为 false
    // 而不可达。此处仅按数据中心格式保留地址形态，代码维持现状；
    // 日后若恢复热更机制，需先在 starrailassistant/Release 下建立 core file_key 并发布版本。
    private const string BaseCoreDownloadUrl =
        "https://data.auto-mas.top/api/v1/files/starrailassistant/Release/core/download";

    private readonly JsonSerializerOptions _jsonSerializerOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        NumberHandling = JsonNumberHandling.AllowReadingFromString
    };

    private readonly Dictionary<int, string> _errorCodes = new()
    {
        { 1001, global::SRAFrontend.Localization.UiText.T("获取版本信息的URL参数不正确") },
        { 7001, global::SRAFrontend.Localization.UiText.T("填入的 CDK 已过期") },
        { 7002, global::SRAFrontend.Localization.UiText.T("填入的 CDK 错误") },
        { 7003, global::SRAFrontend.Localization.UiText.T("填入的 CDK 今日下载次数已达上限") },
        { 7004, global::SRAFrontend.Localization.UiText.T("填入的 CDK 类型和待下载的资源不匹配") },
        { 7005, global::SRAFrontend.Localization.UiText.T("填入的 CDK 已被封禁") },
        { 8001, global::SRAFrontend.Localization.UiText.T("对应架构和系统下的资源不存在") },
        { 8002, global::SRAFrontend.Localization.UiText.T("错误的系统参数") },
        { 8003, global::SRAFrontend.Localization.UiText.T("错误的架构参数") },
        { 8004, global::SRAFrontend.Localization.UiText.T("错误的更新通道参数") }
    };

    public async Task<VersionResponse?> VerifyCdkAsync(string cdk)
    {
        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        var response = await httpClient.GetAsync($"{BaseVersionUrl}?cdk={cdk}");
        return await response.Content.ReadFromJsonAsync<VersionResponse>(_jsonSerializerOptions);
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
            return await response.Content.ReadFromJsonAsync<VersionResponse>(_jsonSerializerOptions);
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
    /// <param name="downloadChannel">下载渠道（0=Mirror酱，1=GitHub，2=Auto-MAS）</param>
    /// <param name="updateChannel">更新通道（stable/beta），仅 Auto-MAS 渠道使用</param>
    /// <param name="statusProgress">下载状态回调</param>
    /// <param name="cancellationToken">取消下载Token</param>
    /// <param name="downloadDir">安装包保存目录，为 null/空白时使用默认临时目录</param>
    /// <returns>更新文件的路径</returns>
    /// <exception cref="Exception"></exception>
    public async Task<string> DownloadUpdateAsync(
        VersionResponse versionResponse,
        int downloadChannel,
        string updateChannel,
        IProgress<DownloadStatus> statusProgress,
        CancellationToken cancellationToken = default,
        string? downloadDir = null
    )
    {
        var version = versionResponse.Data.VersionName;
        var downloadUrl = await GetDownloadUrlAsync(versionResponse, downloadChannel, updateChannel,
            cancellationToken);
        var sha256 = await GetSha256Async(versionResponse,
            cancellationToken);

        return await DownloadPackageAsync(version, downloadUrl, sha256, statusProgress,
            cancellationToken, downloadDir);
    }

    /// <summary>
    ///     重新安装最新版本：获取最新版本信息后下载其完整安装包（不做版本高低比较，
    ///     当前已是最新版时同样重新下载安装）。缓存命中且 SHA256 校验通过时直接复用。
    /// </summary>
    /// <param name="downloadChannel">下载渠道（0=Mirror酱，1=GitHub，2=Auto-MAS）</param>
    /// <param name="statusProgress">下载状态回调</param>
    /// <param name="channel">更新通道（stable/beta）</param>
    /// <param name="cdk">Mirror酱 CDK（可选）</param>
    /// <param name="cancellationToken">取消下载 Token</param>
    /// <param name="downloadDir">安装包保存目录，为 null/空白时使用默认临时目录</param>
    /// <returns>最新版本信息与已校验安装包的本地路径</returns>
    /// <exception cref="InvalidOperationException">无法获取最新版本信息</exception>
    public async Task<(VersionResponse VersionResponse, string PackagePath)> ReinstallLatestVersionAsync(
        int downloadChannel,
        IProgress<DownloadStatus> statusProgress,
        string channel,
        string? cdk = null,
        CancellationToken cancellationToken = default,
        string? downloadDir = null
    )
    {
        logger.LogInformation("Reinstalling latest version package");
        var response = await GetRemoteVersionAsync(null, cdk, channel)
                       ?? throw new InvalidOperationException(
                           "Could not get the latest version information. Please check your network connection or try again later.");

        var packagePath = await DownloadUpdateAsync(
            response, downloadChannel, channel, statusProgress, cancellationToken, downloadDir);
        return (response, packagePath);
    }

    /// <summary>
    ///     解析安装包保存目录：自定义目录为空白时回退到默认临时目录，并确保目录存在。
    /// </summary>
    private static string ResolveDownloadDir(string? downloadDir)
    {
        var dir = string.IsNullOrWhiteSpace(downloadDir) ? DataPath.TempDir : downloadDir.Trim();
        Directory.CreateDirectory(dir);
        return dir;
    }

    /// <summary>
    ///     下载（或复用缓存的）指定版本安装包，并严格执行 SHA256 校验。
    ///     缓存校验失败会删除重下；下载完成后再次校验，失败则删除文件并抛出异常。
    /// </summary>
    private async Task<string> DownloadPackageAsync(
        string version,
        string downloadUrl,
        string sha256,
        IProgress<DownloadStatus> statusProgress,
        CancellationToken cancellationToken,
        string? downloadDir = null
    )
    {
        var savePath = Path.Combine(ResolveDownloadDir(downloadDir), $"update_{version}.zip");

        // 1. 如果已有缓存文件，则先校验
        if (File.Exists(savePath))
        {
            logger.LogInformation("Found cached update file, verifying SHA256: {Path}", savePath);
            if (await VerifyFileSha256Async(savePath, sha256, cancellationToken))
            {
                logger.LogInformation("Cached update file passed SHA256 verification, reuse it.");
                return savePath;
            }

            logger.LogWarning("Cached update file failed SHA256 verification, deleting: {Path}", savePath);
            File.Delete(savePath);
        }

        // 2. 下载文件
        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        logger.LogDebug("Downloading update package from {Url}", downloadUrl);
        await DownloadUtil.DownloadFileWithDetailsAsync(
            httpClient,
            downloadUrl,
            savePath,
            statusProgress,
            cancellationToken
        );

        // 3. 下载后再校验一次
        if (await VerifyFileSha256Async(savePath, sha256, cancellationToken)) return savePath;
        File.Delete(savePath);
        throw new InvalidOperationException(
            "Failed to verify the downloaded update package's SHA256. The file has been deleted.");

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
        // 数据中心按 file 的已发布版本提供服务，下载地址不含版本号，无需再替换 {version} 占位符
        var downloadUrl = BaseCoreDownloadUrl;
        logger.LogDebug("Downloading hotfix from URL: {Url}", downloadUrl);
        var saveFileName = $"core_update_{hotfixVersion}.zip";
        var savePath = Path.Combine(DataPath.TempDir, saveFileName);
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
        if (await VerifyFileSha256Async(savePath, sha256, cancellationToken)) return savePath;
        File.Delete(savePath);
        throw new InvalidOperationException("Downloaded hotfix file failed SHA256 verification.");

    }

    // 辅助方法：获取下载URL
    private async Task<string> GetDownloadUrlAsync(VersionResponse versionResponse, int downloadChannel,
        string updateChannel, CancellationToken cancellationToken)
    {
        if (string.IsNullOrEmpty(versionResponse.Data.Url) || downloadChannel == 2)
        {
            var publishedVersion = await FetchDataCenterMetadataAsync(updateChannel, cancellationToken);
            var expectedFileName = $"StarRailAssistant_{versionResponse.Data.VersionName}.zip";
            if (!string.Equals(publishedVersion.SourceFilename, expectedFileName,
                    StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException(
                    $"""
                     The Auto-MAS data center is serving {publishedVersion.SourceFilename},
                     which does not match the latest version {versionResponse.Data.VersionName}. It may not have been synced yet.
                     Please try again later or switch the download channel in settings.
                     """);
            versionResponse.Data.PublishedVersion = publishedVersion;
            return BuildDataCenterUrl(updateChannel);
        }
        if (downloadChannel == 1)
            return BaseDownloadUrl.Replace("{version}", versionResponse.Data.VersionName);
        return versionResponse.Data.Url;
    }

    /// <summary>
    ///     拼接数据中心下载地址，并把通道收敛到 stable/beta，避免异常取值拼出无效 URL。
    /// </summary>
    private static string BuildDataCenterMetadataUrl(string? updateChannel) =>
        DataCenterReleaseMetadataUrl.Replace("{channel}",
            string.Equals(updateChannel, "beta", StringComparison.OrdinalIgnoreCase) ? "beta" : "stable");

    private static string BuildDataCenterUrl(string? updateChannel) =>
        $"{BuildDataCenterMetadataUrl(updateChannel)}/download";

    /// <summary>
    ///     获取数据中心元数据，取出包内哈希与服务端保存的原始文件名。
    /// </summary>
    private async Task<PublishedVersion> FetchDataCenterMetadataAsync(string updateChannel,
        CancellationToken cancellationToken=default)
    {
        var metadataUrl = BuildDataCenterMetadataUrl(updateChannel);
        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        using var response = await httpClient.GetAsync(metadataUrl, cancellationToken);
        response.EnsureSuccessStatusCode();
        var metadata = await response.Content.ReadFromJsonAsync<VersionResponse>(_jsonSerializerOptions,
            cancellationToken);
        var publishedVersion = metadata?.Data.PublishedVersion
                               ?? throw new InvalidOperationException(
                                   "The Auto-MAS data center did not return package metadata.");
        return publishedVersion;
    }

    /// <summary>
    ///     按优先级获取安装包 SHA256：
    ///     1. versionResponse 中已有值；
    ///     2. Auto-MAS 对应 channel 的元数据；
    ///     3. GitHub 对应 Release 的完整安装包 asset digest。
    ///     所有来源均不可用时返回空值，此时沿用未提供 SHA256 时跳过校验的既有行为。
    /// </summary>
    private async Task<string> GetSha256Async(VersionResponse versionResponse,
        CancellationToken cancellationToken)
    {
        var responseSha256 = versionResponse.Data.Sha256?.Trim();
        if (string.IsNullOrEmpty(responseSha256))
            responseSha256 = versionResponse.Data.PublishedVersion?.Sha256.Trim();

        if (!string.IsNullOrEmpty(responseSha256))
            return responseSha256.ToLowerInvariant();

        var httpClient = httpClientFactory.CreateClient("GlobalClient");

        try
        {
            var url = GitHubReleaseMetadataUrl.Replace("{version}", versionResponse.Data.VersionName);
            using var response = await httpClient.GetAsync(url, cancellationToken);
            response.EnsureSuccessStatusCode();
            var release = await response.Content.ReadFromJsonAsync<GitHubReleaseMetadata>(
                _jsonSerializerOptions, cancellationToken);
            var assetName = $"StarRailAssistant_{versionResponse.Data.VersionName}.zip";
            var digest = release?.Assets.Find(asset =>
                    string.Equals(asset.Name, assetName, StringComparison.OrdinalIgnoreCase))
                ?.Digest;
            const string sha256Prefix = "sha256:";
            if (!string.IsNullOrWhiteSpace(digest) &&
                digest.StartsWith(sha256Prefix, StringComparison.OrdinalIgnoreCase))
                return digest[sha256Prefix.Length..].Trim().ToLowerInvariant();
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception exception)
        {
            logger.LogDebug(exception, "Failed to get SHA256 from GitHub release metadata.");
        }

        return "";
    }

    private sealed class GitHubReleaseMetadata
    {
        public List<GitHubReleaseAsset> Assets { get; init; } = [];
    }

    private record GitHubReleaseAsset(string Name, string? Digest);

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
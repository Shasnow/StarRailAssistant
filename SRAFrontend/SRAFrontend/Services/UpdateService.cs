using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
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

    private const string DataCenterBaseUrl = "https://data.auto-mas.top";

    private const string DataCenterDownloadUrl =
        "https://data.auto-mas.top/api/v1/files/starrailassistant/Release/{channel}/download";

    // 数据中心目前没有热更包（Core）产物：旧站 download.auto-mas.top 上该资源已长期未上传
    // （实测返回 500 object not found），客户端侧 DownloadHotfixAsync 也因 isHotfix 恒为 false
    // 而不可达。此处仅按数据中心格式保留地址形态，代码维持现状；
    // 日后若恢复热更机制，需先在 starrailassistant/Release 下建立 core file_key 并发布版本。
    private const string BaseCoreDownloadUrl =
        "https://data.auto-mas.top/api/v1/files/starrailassistant/Release/core/download";

    // 数据中心产出的完整包名为 StarRailAssistant_v2.23.1.zip（beta 形如 ..._v2.23.2-beta.1.zip）。
    // 前缀写死 StarRailAssistant_v，避免把 Resources/Core/Lite 等同目录产物误判为完整包。
    private static readonly Regex DataCenterFileNameRegex = new(
        @"StarRailAssistant_v(\d+\.\d+\.\d+(?:-[0-9A-Za-z.\-]+)?)\.zip$",
        RegexOptions.Compiled | RegexOptions.IgnoreCase);

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
        string? updateChannel,
        IProgress<DownloadStatus> statusProgress,
        CancellationToken cancellationToken = default,
        string? downloadDir = null
    )
    {
        var version = versionResponse.Data.VersionName;
        var downloadUrl = GetDownloadUrl(versionResponse, downloadChannel, updateChannel);
        var sha256 = await GetExpectedSha256Async(downloadUrl, versionResponse, cancellationToken);

        return await DownloadPackageAsync(version, downloadUrl, sha256, statusProgress,
            cancellationToken, downloadDir);
    }

    /// <summary>
    ///     重新安装最新版本：获取最新版本信息后下载其完整安装包（不做版本高低比较，
    ///     当前已是最新版时同样重新下载安装）。缓存命中且 SHA256 校验通过时直接复用。
    /// </summary>
    /// <param name="downloadChannel">下载渠道（0=Mirror酱，1=GitHub，2=Auto-MAS）</param>
    /// <param name="statusProgress">下载状态回调</param>
    /// <param name="cdk">Mirror酱 CDK（可选）</param>
    /// <param name="channel">更新通道（stable/beta）</param>
    /// <param name="cancellationToken">取消下载 Token</param>
    /// <param name="downloadDir">安装包保存目录，为 null/空白时使用默认临时目录</param>
    /// <returns>最新版本信息与已校验安装包的本地路径</returns>
    /// <exception cref="InvalidOperationException">无法获取最新版本信息</exception>
    public async Task<(VersionResponse VersionResponse, string PackagePath)> ReinstallLatestVersionAsync(
        int downloadChannel,
        IProgress<DownloadStatus> statusProgress,
        string? cdk = null,
        string? channel = null,
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
    private static string GetDownloadUrl(VersionResponse versionResponse, int downloadChannel,
        string? updateChannel)
    {
        if (string.IsNullOrEmpty(versionResponse.Data.Url) || downloadChannel == 2)
            return BuildDataCenterUrl(updateChannel);
        if (downloadChannel == 1)
            return BaseDownloadUrl.Replace("{version}", versionResponse.Data.VersionName);
        return versionResponse.Data.Url;
    }

    /// <summary>
    ///     拼接数据中心下载地址，并把通道收敛到 stable/beta，避免异常取值拼出无效 URL。
    /// </summary>
    private static string BuildDataCenterUrl(string? updateChannel) =>
        DataCenterDownloadUrl.Replace("{channel}",
            string.Equals(updateChannel, "beta", StringComparison.OrdinalIgnoreCase) ? "beta" : "stable");

    private static bool IsDataCenterUrl(string url) =>
        url.StartsWith(DataCenterBaseUrl, StringComparison.OrdinalIgnoreCase);

    /// <summary>
    ///     解析本次下载应使用的 SHA256。
    ///
    ///     数据中心渠道：哈希取自服务端 Repr-Digest，并额外用文件名里的版本号做一次漂移校验
    ///     （mirrorchyan 无 CDK 时不返回 sha256，因此不能依赖哈希做跨源比对）。
    ///     其余渠道：沿用 mirrorchyan 返回的 sha256，未填 CDK 时为空、跳过校验。
    /// </summary>
    private async Task<string> GetExpectedSha256Async(string downloadUrl, VersionResponse versionResponse,
        CancellationToken cancellationToken)
    {
        if (!IsDataCenterUrl(downloadUrl))
            return await GetSha256Async(versionResponse, cancellationToken);

        var (sha256, fileName) = await FetchDataCenterMetadataAsync(downloadUrl, cancellationToken);
        EnsureDataCenterVersionMatches(fileName, versionResponse.Data.VersionName);
        return sha256;
    }

    /// <summary>
    ///     HEAD 一次数据中心下载地址，取出包内哈希（Repr-Digest）与服务端保存的原始文件名。
    /// </summary>
    private async Task<(string Sha256, string FileName)> FetchDataCenterMetadataAsync(string url,
        CancellationToken cancellationToken)
    {
        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        using var request = new HttpRequestMessage(HttpMethod.Head, url);
        using var response = await httpClient.SendAsync(request, HttpCompletionOption.ResponseHeadersRead,
            cancellationToken);

        if (!response.IsSuccessStatusCode)
            throw new InvalidOperationException(
                $"The Auto-MAS data center returned {(int)response.StatusCode} for the update package. " +
                "Please check your network connection or switch the download channel in settings.");

        var sha256 = TryParseReprDigestSha256(response)
                     ?? throw new InvalidOperationException(
                         "The Auto-MAS data center did not return a usable Repr-Digest, so the update " +
                         "package cannot be verified. Please switch the download channel in settings.");

        var fileName = GetContentDispositionFileName(response) ?? "";
        logger.LogDebug("Data center package: {FileName} (sha-256 {Sha256})", fileName, sha256);
        return (sha256, fileName);
    }

    /// <summary>
    ///     校验数据中心实际提供的版本与 mirrorchyan 报告的最新版本一致。
    ///
    ///     数据中心的 published_version_no 是每个 file 自增的整数，不是应用版本号，
    ///     因此只能从 Content-Disposition 的文件名（如 StarRailAssistant_v2.23.1.zip）里取版本。
    ///     不一致说明数据中心尚未同步到该版本，此时必须明确失败——否则会静默装回旧版本，
    ///     下次启动又提示更新，陷入「检查更新 → 装旧版 → 再提示」的循环。
    /// </summary>
    private static void EnsureDataCenterVersionMatches(string fileName, string remoteVersionName)
    {
        var servedVersion = ExtractVersionFromFileName(fileName);
        var served = SemVerParser.Parse(servedVersion);
        var remote = SemVerParser.Parse(remoteVersionName);

        // SemVerInfo 未重写 ==/Equals，只能靠 CompareTo 判断相等
        if (served is not null && remote is not null && served.CompareTo(remote) == 0)
            return;

        var servedDescription = servedVersion
                                ?? (string.IsNullOrEmpty(fileName) ? "an unknown version" : fileName);
        throw new InvalidOperationException(
            $"The Auto-MAS data center is serving {servedDescription}, " +
            $"which does not match the latest version {remoteVersionName}. It may not have been synced yet. " +
            "Please try again later or switch the download channel in settings.");
    }

    /// <summary>
    ///     从 Content-Disposition 取服务端保存的原始文件名。
    /// </summary>
    private static string? GetContentDispositionFileName(HttpResponseMessage response)
    {
        var disposition = response.Content.Headers.ContentDisposition;
        var fileName = disposition?.FileNameStar ?? disposition?.FileName;
        if (string.IsNullOrWhiteSpace(fileName)) return null;

        // 个别实现会把 RFC 5987 的 charset'' 前缀一起带出来，这里兜底清掉
        var value = Regex.Replace(fileName.Trim().Trim('"'), @"^[A-Za-z0-9\-]+''", "");
        return value.Trim().Trim('"');
    }

    /// <summary>
    ///     从 StarRailAssistant_v2.23.1.zip / StarRailAssistant_v2.23.2-beta.1.zip 中取出版本号。
    /// </summary>
    private static string? ExtractVersionFromFileName(string fileName)
    {
        if (string.IsNullOrWhiteSpace(fileName)) return null;
        var match = DataCenterFileNameRegex.Match(fileName.Trim());
        return match.Success ? match.Groups[1].Value : null;
    }

    /// <summary>
    ///     解析 RFC 9530 的 Repr-Digest，取出 sha-256 的小写十六进制。
    /// </summary>
    private static string? TryParseReprDigestSha256(HttpResponseMessage response)
    {
        if (TryParseReprDigest(response.Headers, out var digest)) return digest;
        if (TryParseReprDigest(response.Content.Headers, out digest)) return digest;
        return null;
    }

    private static bool TryParseReprDigest(HttpHeaders headers, out string? digest)
    {
        digest = null;
        if (!headers.TryGetValues("Repr-Digest", out var values)) return false;

        foreach (var raw in values)
        foreach (var member in raw.Split(','))
        {
            var part = member.Trim();
            // 用第一个 '=' 分隔算法与取值，base64 的 '=' 填充不受影响
            var separator = part.IndexOf('=');
            if (separator <= 0) continue;

            var algorithm = part[..separator].Trim();
            var parameter = algorithm.IndexOf(';');
            if (parameter >= 0) algorithm = algorithm[..parameter].Trim();
            if (!string.Equals(algorithm.Replace("-", ""), "sha256", StringComparison.OrdinalIgnoreCase))
                continue;

            // RFC 9530 的字节序列用冒号包裹：sha-256=:<base64>:
            var value = part[(separator + 1)..].Trim();
            if (value.Length < 2 || value[0] != ':' || value[^1] != ':') continue;

            try
            {
                var base64 = value[1..^1].Trim();
                var remainder = base64.Length % 4;
                if (remainder != 0) base64 = base64.PadRight(base64.Length + (4 - remainder), '=');

                var bytes = Convert.FromBase64String(base64);
                if (bytes.Length != 32) continue; // 必须是 32 字节的 SHA-256
                digest = Convert.ToHexString(bytes).ToLowerInvariant();
                return true;
            }
            catch (FormatException)
            {
                // 该成员格式非法，继续尝试下一个
            }
        }

        return false;
    }

    /// <summary>
    ///     获取 mirrorchyan 提供的 SHA256。
    ///
    ///     旧站的 .sha256 旁路文件随旧站一起退役，这里不再有回退来源；未填 CDK 时该值为空，
    ///     此时 VerifyFileSha256Async 会跳过校验（既有行为）。
    /// </summary>
    private Task<string> GetSha256Async(VersionResponse versionResponse, CancellationToken cancellationToken) =>
        Task.FromResult(versionResponse.Data.Sha256?.Trim().ToLowerInvariant() ?? "");

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
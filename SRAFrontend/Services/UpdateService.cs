using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using System.Security.Cryptography;
using System.IO.Compression;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.utilities;

namespace SRAFrontend.Services;

public class UpdateService(IHttpClientFactory httpClientFactory, ILogger<UpdateService> logger)
{
    private const string BaseVersionUrl =
        "https://mirrorchyan.com/api/resources/StarRailAssistant/latest";

    private const string BaseDownloadUrl =
        "https://github.com/Shasnow/StarRailAssistant/releases/download/{version}/StarRailAssistant_{version}.zip";
    
    private const string BaseDownloadUrl2 =
        "https://download.auto-mas.top/d/StarRailAssistant/StarRailAssistant-{version}.zip";
    
    private const string BaseCoreDownloadUrl =
        "https://download.auto-mas.top/d/StarRailAssistant/StarRailAssistant_Core_{version}.zip";

    // Gitee 提供的资源校验信息 API
    private const string GiteeSha256Url =
        "https://gitee.com/yukikage/sraresource/raw/main/SRA/api.json";

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

    private readonly HttpClient _httpClient = httpClientFactory.CreateClient("GlobalClient");

    public async Task<VersionResponse?> VerifyCdkAsync(string cdk)
    {
        var response = await _httpClient.GetAsync($"{BaseVersionUrl}?cdk={cdk}");
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
            url += "?user_agent=SRA_avalonia" + string.Join("&", queryParams);

        var response = await _httpClient.GetAsync(url);
        return await response.Content.ReadFromJsonAsync<VersionResponse>();
    }

    /// <summary>
    /// 异步下载更新包
    /// </summary>
    /// <param name="versionResponse">版本响应模型</param>
    /// <param name="downloadChannel">下载渠道</param>
    /// <param name="statusProgress">下载状态回调</param>
    /// <param name="proxies">代理列表</param>
    /// <param name="cancellationToken">取消下载Token</param>
    /// <returns>更新文件的路径</returns>
    /// <exception cref="InvalidOperationException">下载地址无效或下载失败</exception>
    /// <exception cref="Exception"></exception>
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
            throw new InvalidOperationException("Could not determine download URL.");

        var saveFileName = $"update_{versionResponse.Data.VersionName}.zip";
        var savePath = Path.Combine(PathString.TempSraDir, saveFileName);
        Directory.CreateDirectory(Path.GetDirectoryName(savePath)!);

        // 下载前：先获取期望的校验值并校验本地文件，避免重复下载
        string? expectedSha256 = null;
        if (downloadChannel == 1)
        {
            // GitHub 渠道：从 Gitee 的 api.json 获取 sha256 进行校验
            // expectedSha256 = await TryGetSha256FromGiteeAsync(versionResponse.Data.VersionName, cancellationToken);
            
            // GitHub 渠道：仅当更新通道为 stable 时，使用 Gitee 的 sha256 进行校验
            var isStable = string.Equals(versionResponse.Data.Channel, "stable", StringComparison.OrdinalIgnoreCase);
            if (isStable)
            {
                expectedSha256 = await TryGetSha256FromGiteeAsync(versionResponse.Data.VersionName, cancellationToken);
            }
            else
            {
                expectedSha256 = null; // 非 stable 不进行 sha 校验
            }
        }
        else
        {
            // mirror渠道：使用 VersionResponse 传入的 sha256
            expectedSha256 = versionResponse.Data.Sha256?.Trim();
        }
        var parsedExpected = ExtractSha256(expectedSha256 ?? "");

        if (IsLocalPackageValid(savePath, parsedExpected))
        {
                logger.LogInformation("检测到本地已存在有效更新包，跳过下载：{Path}", savePath);
            return savePath;
        }
        else if (File.Exists(savePath))
        {
            // 本地存在但校验不通过，删除后继续下载
            try { File.Delete(savePath); } catch { /* ignore */ }
        }

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
                logger.LogDebug("尝试从此地址下载更新包：{Url}", candidateUrl);
                await DownloadUtil.DownloadFileWithDetailsAsync(
                    _httpClient,
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

        if (downloadSuccess)
        {
            // 执行校验（若期望值存在且合法）
            if (!string.IsNullOrEmpty(parsedExpected))
            {
                var actualSha256 = ComputeSHA256(savePath);
                if (!string.Equals(actualSha256, parsedExpected, StringComparison.OrdinalIgnoreCase))
                {
                    logger.LogWarning("下载的更新包 SHA256 校验失败。期望：{Expected}，实际：{Actual}", parsedExpected, actualSha256);
                    if (File.Exists(savePath)) File.Delete(savePath);
                    throw new InvalidOperationException("Downloaded update file hash mismatch.");
                }
            }

            return savePath;
        }
        
        if (File.Exists(savePath)) File.Delete(savePath);
        throw lastException ?? new InvalidOperationException("Failed to download update.");

    }

    public async Task<string> DownloadHotfixAsync(
        VersionResponse versionResponse,
        IProgress<DownloadStatus> statusProgress,
        CancellationToken cancellationToken = default
    )
    {
        // 确定下载URL和保存路径
        var hotfixVersion = versionResponse.Data.VersionName;
        var downloadUrl = BaseCoreDownloadUrl.Replace("{version}", hotfixVersion);
        logger.LogDebug("开始下载核心热修补包，来源：{Url}", downloadUrl);
        var saveFileName = $"core_update_{hotfixVersion}.zip";
        var savePath = Path.Combine(PathString.TempSraDir, saveFileName);
        Directory.CreateDirectory(Path.GetDirectoryName(savePath)!);

        // 下载前：若本地已存在，先进行校验，避免重复下载
        var expectedSha256 = versionResponse.Data.Sha256?.Trim();
        var parsedExpected = ExtractSha256(expectedSha256 ?? "");
        if (IsLocalPackageValid(savePath, parsedExpected))
        {
                logger.LogInformation("检测到本地已存在有效热修补包，跳过下载：{Path}", savePath);
            return savePath;
        }
        else if (File.Exists(savePath))
        {
            try { File.Delete(savePath); } catch { /* ignore */ }
        }

        // 尝试下载
        await DownloadUtil.DownloadFileWithDetailsAsync(
            _httpClient,
            downloadUrl,
            savePath,
            statusProgress,
            cancellationToken
        );

        // 校验 SHA256（若远端提供）
        if (!string.IsNullOrEmpty(parsedExpected))
        {
            var actualSha256 = ComputeSHA256(savePath);
            if (!string.Equals(actualSha256, parsedExpected, StringComparison.OrdinalIgnoreCase))
            {
                logger.LogWarning("下载的热修补包 SHA256 校验失败。期望：{Expected}，实际：{Actual}", parsedExpected, actualSha256);
                if (File.Exists(savePath)) File.Delete(savePath);
                throw new InvalidOperationException("Downloaded hotfix file hash mismatch.");
            }
        }

        return savePath;
    }

    // 简单校验ZIP是否有效：能否正常打开
    private static bool IsZipValid(string filePath)
    {
        try
        {
            using var archive = ZipFile.OpenRead(filePath);
            // 能正常打开即认为有效；不要求含有条目
            return true;
        }
        catch
        {
            return false;
        }
    }
    
    // 复用的本地包有效性校验：优先用 SHA256，其次尝试打开ZIP
    private static bool IsLocalPackageValid(string filePath, string? parsedExpected)
    {
        if (!File.Exists(filePath)) return false;
        if (!string.IsNullOrEmpty(parsedExpected))
        {
            var actual = ComputeSHA256(filePath);
            return string.Equals(actual, parsedExpected, StringComparison.OrdinalIgnoreCase);
        }
        return IsZipValid(filePath);
    }
    
    // 辅助方法：获取下载URL
    private string GetDownloadUrl(VersionResponse versionResponse, int downloadChannel)
    {
        if (versionResponse.Data.Url == "" || downloadChannel==2)
            return BaseDownloadUrl2.Replace("{version}", versionResponse.Data.VersionName);
        if (downloadChannel == 1)
            return BaseDownloadUrl.Replace("{version}", versionResponse.Data.VersionName);
        return versionResponse.Data.Url;
    }

    // 计算文件的 SHA256（小写十六进制）
    private static string ComputeSHA256(string filePath)
    {
        using var stream = File.OpenRead(filePath);
        using var sha256 = SHA256.Create();
        var hash = sha256.ComputeHash(stream);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    
    // 尝试从 Gitee 的 api.json 获取 SHA256
    private async Task<string?> TryGetSha256FromGiteeAsync(string versionName, CancellationToken cancellationToken)
    {
        var url = GiteeSha256Url;
        try
        {
            using var req = new HttpRequestMessage(HttpMethod.Get, url);
            req.Headers.UserAgent.ParseAdd("SRAFrontend/1.0");
            req.Headers.Accept.ParseAdd("application/json");
            using var resp = await _httpClient.SendAsync(req, cancellationToken);
            if (!resp.IsSuccessStatusCode)
            {
                logger.LogDebug("从 Gitee 获取校验信息失败，HTTP 状态：{Status}", resp.StatusCode);
                return null;
            }

            var text = await resp.Content.ReadAsStringAsync(cancellationToken);
            using var doc = JsonDocument.Parse(text);
            string? name = null;
            string? sha = null;
            if (doc.RootElement.TryGetProperty("name", out var nameProp)) name = nameProp.GetString();
            if (doc.RootElement.TryGetProperty("sha256", out var shaProp)) sha = shaProp.GetString();

            if (!string.IsNullOrWhiteSpace(sha))
            {
                // 若 name 可用且包含版本号，进一步确认匹配
                if (!string.IsNullOrWhiteSpace(name) && !name.Contains(versionName, StringComparison.OrdinalIgnoreCase))
                {
                    logger.LogWarning("Gitee 返回的资源名称与版本不匹配。期望包含：{Version}，实际名称：{Name}", versionName, name);
                }
                // 验证 sha 格式
                var parsed = ExtractSha256(sha);
                if (!string.IsNullOrEmpty(parsed)) return parsed;
            }
        }
        catch (Exception ex)
        {
            logger.LogDebug("从 Gitee 获取 sha256 时发生错误：{Message}", ex.Message);
        }
        return null;
    }

    // 从文本中提取 SHA256：优先寻找长度为64的十六进制串
    private static string? ExtractSha256(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return null;
        var simplified = text.Replace("\r", "\n");
        var lines = simplified.Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        foreach (var line in lines)
        {
            var s = line.Trim();
            // 常见格式：<sha256>  <filename>
            // 尝试匹配首个 64 位 hex
            var sha = FirstHex64(s);
            if (!string.IsNullOrEmpty(sha)) return sha.ToLowerInvariant();
        }
        return null;
    }

    private static string? FirstHex64(string s)
    {
        // 扫描字符串，取出第一个长度>=64的 hex 片段
        int start = -1;
        int count = 0;
        for (int i = 0; i < s.Length; i++)
        {
            if (IsHexChar(s[i]))
            {
                if (start == -1) start = i;
                count++;
                if (count >= 64)
                {
                    var candidate = s.Substring(start, 64);
                    // 校验是否纯 hex
                    if (candidate.All(IsHexChar)) return candidate;
                    // 否则继续滑动
                    start = -1;
                    count = 0;
                }
            }
            else
            {
                start = -1;
                count = 0;
            }
        }
        return null;
    }

    private static bool IsHexChar(char c)
    {
        return (c >= '0' && c <= '9') ||
               (c >= 'a' && c <= 'f') ||
               (c >= 'A' && c <= 'F');
    }
}
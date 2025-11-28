using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
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
                logger.LogDebug("Try downloading update from: {Url} ", candidateUrl);
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

        if (downloadSuccess) return savePath;
        
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
        logger.LogDebug("Downloading hotfix from URL: {Url}", downloadUrl);
        var saveFileName = $"core_update_{hotfixVersion}.zip";
        var savePath = Path.Combine(PathString.TempSraDir, saveFileName);
        Directory.CreateDirectory(Path.GetDirectoryName(savePath)!);

        // 尝试下载
        await DownloadUtil.DownloadFileWithDetailsAsync(
            _httpClient,
            downloadUrl,
            savePath,
            statusProgress,
            cancellationToken
        );

        return savePath;
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
}
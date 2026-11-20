using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Utils;

namespace SRAFrontend.Services;

/// <summary>
///     patch 级热更新：拉取差量清单、逐文件下载校验并原地替换应用目录中的运行时文件。
/// </summary>
public class HotfixService(IHttpClientFactory httpClientFactory, ILogger<HotfixService> logger)
{
    private const string DocsManifestBaseUrl = "https://starrailassistant.top/api/v1/hotfix";
    private const string R2ManifestBaseUrl = "https://resource.starrailassistant.top/hotfix";

    private static readonly string[] DefaultSources =
    [
        "https://cnb.cool/StarRailAssistant/StarRailAssistant/-/git/raw/v{version}/{path}",
        "https://raw.githubusercontent.com/Shasnow/StarRailAssistant/v{version}/{path}"
    ];

    /// <summary>
    ///     判断远端 patch 版本是否可热更新，并返回对应清单；不满足条件时返回 null。
    /// </summary>
    /// <param name="effectiveVersion">当前有效版本（程序版本与已装热修取较大者）</param>
    /// <param name="remoteVersion">远端版本</param>
    /// <param name="updateChannel">更新通道，0=Stable</param>
    /// <param name="cancellationToken">取消 Token</param>
    public async Task<HotfixManifest?> GetApplicableManifestAsync(
        SemVerInfo effectiveVersion,
        SemVerInfo remoteVersion,
        int updateChannel,
        CancellationToken cancellationToken = default)
    {
        if (updateChannel != 0) return null;
        if (effectiveVersion.PreRelease != null || remoteVersion.PreRelease != null) return null;
        if (remoteVersion.Major != effectiveVersion.Major ||
            remoteVersion.Minor != effectiveVersion.Minor ||
            remoteVersion.Patch <= effectiveVersion.Patch)
            return null;

        var manifest = await GetManifestAsync(remoteVersion.ToString(), cancellationToken);
        if (manifest == null) return null;
        if (!string.Equals(manifest.Version, remoteVersion.ToString(), StringComparison.OrdinalIgnoreCase))
        {
            logger.LogWarning(
                "Hotfix manifest version mismatch: expected {Expected}, got {Actual}",
                remoteVersion, manifest.Version);
            return null;
        }

        var baseVersion = SemVerParser.Parse(manifest.BaseVersion);
        if (baseVersion == null ||
            baseVersion.Major != remoteVersion.Major ||
            baseVersion.Minor != remoteVersion.Minor ||
            effectiveVersion < baseVersion)
            return null;

        return manifest;
    }

    /// <summary>
    ///     依次从文档站与 R2 拉取清单，返回首个合法结果。
    /// </summary>
    public async Task<HotfixManifest?> GetManifestAsync(
        string version,
        CancellationToken cancellationToken = default)
    {
        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        foreach (var baseUrl in new[] { DocsManifestBaseUrl, R2ManifestBaseUrl })
        {
            var url = $"{baseUrl}/v{version}.json";
            try
            {
                using var response = await httpClient.GetAsync(url, cancellationToken);
                if (!response.IsSuccessStatusCode)
                {
                    logger.LogDebug("Hotfix manifest unavailable at {Url} (HTTP {Status})", url, (int)response.StatusCode);
                    continue;
                }

                var manifest = await response.Content.ReadFromJsonAsync<HotfixManifest>(
                    JsonSerializerOptions.Web, cancellationToken);
                if (manifest == null || manifest.Schema != 1 || string.IsNullOrWhiteSpace(manifest.Version))
                    continue;
                logger.LogInformation("Loaded hotfix manifest {Version} from {Url}", manifest.Version, url);
                return manifest;
            }
            catch (OperationCanceledException)
            {
                throw;
            }
            catch (Exception e)
            {
                logger.LogDebug(e, "Failed to load hotfix manifest from {Url}", url);
            }
        }

        return null;
    }

    /// <summary>
    ///     下载清单中本地缺失或哈希不一致的文件到暂存目录，并逐个校验 SHA-256。
    /// </summary>
    /// <returns>实际需要下载的文件数</returns>
    /// <exception cref="InvalidOperationException">任一文件在全部源上都下载或校验失败</exception>
    public async Task<int> DownloadAndStageAsync(
        HotfixManifest manifest,
        string stagingDir,
        IProgress<DownloadStatus> progress,
        CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(stagingDir);

        var pending = new List<HotfixFile>();
        long totalBytes = 0;
        foreach (var file in manifest.Files)
        {
            var localPath = ResolveTarget(file.Path);
            if (File.Exists(localPath) &&
                await VerifySha256Async(localPath, file.Sha256, cancellationToken))
                continue;
            pending.Add(file);
            totalBytes += file.Size;
        }

        if (pending.Count == 0) return 0;

        var httpClient = httpClientFactory.CreateClient("GlobalClient");
        long completedBytes = 0;
        foreach (var file in pending)
        {
            var target = Path.Combine(stagingDir, file.Path);
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            await DownloadFromSourcesAsync(
                httpClient, manifest, file, target, completedBytes, totalBytes, progress, cancellationToken);
            completedBytes += file.Size;
        }

        return pending.Count;
    }

    /// <summary>
    ///     应用暂存文件：覆盖目标文件、删除清单中的废弃文件，并同步更新 manifest.md5.json。
    /// </summary>
    public async Task ApplyAsync(
        HotfixManifest manifest,
        string stagingDir,
        CancellationToken cancellationToken = default)
    {
        var changedMd5 = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var file in manifest.Files)
        {
            var target = ResolveTarget(file.Path);
            var staged = Path.Combine(stagingDir, file.Path);
            if (File.Exists(staged))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                File.Copy(staged, target, true);
            }

            if (File.Exists(target))
                changedMd5[file.Path] = await ComputeMd5Async(target, cancellationToken);
        }

        foreach (var relativePath in manifest.Deleted)
        {
            try
            {
                var target = ResolveTarget(relativePath);
                if (File.Exists(target)) File.Delete(target);
            }
            catch (Exception e)
            {
                logger.LogWarning(e, "Failed to delete obsolete hotfix file: {Path}", relativePath);
            }
        }

        ZipUtil.UpdateManifest(DataPath.AppRoot, changedMd5, manifest.Deleted);
        CleanupStaging(stagingDir);
    }

    /// <summary>删除下载暂存目录（失败仅记录日志）。</summary>
    public static void CleanupStaging(string stagingDir)
    {
        try
        {
            if (Directory.Exists(stagingDir)) Directory.Delete(stagingDir, true);
        }
        catch
        {
            // 暂存目录位于临时目录，残留不影响应用
        }
    }

    private async Task DownloadFromSourcesAsync(
        HttpClient httpClient,
        HotfixManifest manifest,
        HotfixFile file,
        string target,
        long completedBytes,
        long totalBytes,
        IProgress<DownloadStatus> progress,
        CancellationToken cancellationToken)
    {
        var sources = manifest.Sources.Count > 0 ? manifest.Sources : DefaultSources.ToList();
        Exception? lastError = null;
        foreach (var source in sources)
        {
            var url = source
                .Replace("{version}", Uri.EscapeDataString(manifest.Version))
                .Replace("{path}", EncodePath(file.Path));
            try
            {
                await DownloadUtil.DownloadFileWithDetailsAsync(
                    httpClient, url, target, progress, cancellationToken, completedBytes, totalBytes);
                if (await VerifySha256Async(target, file.Sha256, cancellationToken)) return;
                lastError = new InvalidDataException($"SHA-256 mismatch for {file.Path}");
                logger.LogWarning("Hotfix file hash mismatch from {Url}", url);
            }
            catch (OperationCanceledException)
            {
                throw;
            }
            catch (Exception e)
            {
                lastError = e;
                logger.LogDebug(e, "Failed to download hotfix file from {Url}", url);
            }

            try
            {
                if (File.Exists(target)) File.Delete(target);
            }
            catch
            {
                // 忽略清理失败，下次写入会覆盖
            }
        }

        throw new InvalidOperationException($"Failed to download hotfix file: {file.Path}", lastError);
    }

    /// <summary>逐段编码路径，保留正斜杠分隔符。</summary>
    private static string EncodePath(string path) =>
        string.Join("/", path.Split('/').Select(Uri.EscapeDataString));

    /// <summary>
    ///     把清单中的相对路径解析到应用根目录，并阻止绝对路径或 .. 逃逸。
    /// </summary>
    private static string ResolveTarget(string relativePath)
    {
        if (string.IsNullOrWhiteSpace(relativePath) || Path.IsPathRooted(relativePath))
            throw new InvalidOperationException($"Invalid hotfix path: {relativePath}");

        var root = Path.GetFullPath(DataPath.AppRoot);
        var rootPrefix = root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)
                         + Path.DirectorySeparatorChar;
        var fullPath = Path.GetFullPath(Path.Combine(root, relativePath));
        var comparison = OperatingSystem.IsWindows()
            ? StringComparison.OrdinalIgnoreCase
            : StringComparison.Ordinal;
        if (!fullPath.StartsWith(rootPrefix, comparison))
            throw new InvalidOperationException($"Hotfix path escapes app root: {relativePath}");
        return fullPath;
    }

    private static async Task<bool> VerifySha256Async(
        string filePath,
        string expectedSha256,
        CancellationToken cancellationToken)
    {
        if (!File.Exists(filePath) || string.IsNullOrWhiteSpace(expectedSha256)) return false;
        var actual = await ComputeSha256Async(filePath, cancellationToken);
        return string.Equals(actual, expectedSha256.Trim(), StringComparison.OrdinalIgnoreCase);
    }

    private static async Task<string> ComputeSha256Async(string filePath, CancellationToken cancellationToken)
    {
        await using var stream = File.OpenRead(filePath);
        var hash = await SHA256.HashDataAsync(stream, cancellationToken);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    private static async Task<string> ComputeMd5Async(string filePath, CancellationToken cancellationToken)
    {
        await using var stream = File.OpenRead(filePath);
        var hash = await MD5.HashDataAsync(stream, cancellationToken);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }
}

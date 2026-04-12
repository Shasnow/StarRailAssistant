using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class ScriptService
{
    private readonly ILogger<ScriptService> _logger;
    private static readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(30) };

    private static readonly string AppDataDir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "SRA");

    public static readonly string ScriptsDir = Path.Combine(AppDataDir, "scripts");
    private static readonly string ReposConfigPath = Path.Combine(AppDataDir, "script_repos.json");

    private static readonly JsonSerializerOptions _json = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        WriteIndented = true
    };

    public ScriptService(ILogger<ScriptService> logger)
    {
        _logger = logger;
        Directory.CreateDirectory(ScriptsDir);
    }

    public List<ScriptRepo> LoadRepos()
    {
        if (!File.Exists(ReposConfigPath)) return [];
        try
        {
            var json = File.ReadAllText(ReposConfigPath);
            var cfg = JsonSerializer.Deserialize<ScriptReposConfig>(json, _json);
            return cfg?.Repos ?? [];
        }
        catch (Exception e)
        {
            _logger.LogError(e, "加载仓库配置失败");
            return [];
        }
    }

    public void SaveRepos(List<ScriptRepo> repos)
    {
        var cfg = new ScriptReposConfig { Repos = repos };
        File.WriteAllText(ReposConfigPath, JsonSerializer.Serialize(cfg, _json));
    }

    /// <summary>
    /// 把 GitHub 仓库 URL 转换为 repo.json 的 raw URL。
    /// 支持：
    ///   https://github.com/user/repo  -> https://raw.githubusercontent.com/user/repo/main/repo.json
    ///   https://github.com/user/repo/tree/branch -> 对应分支
    /// 其他 URL 原样保留。
    /// </summary>
    public static string NormalizeRepoUrl(string url)
    {
        url = url.Trim().TrimEnd('/');
        if (!url.StartsWith("https://github.com/", StringComparison.OrdinalIgnoreCase))
            return url;

        // 去掉 https://github.com/
        var path = url["https://github.com/".Length..];
        var parts = path.Split('/');

        if (parts.Length < 2) return url;

        var user = parts[0];
        var repo = parts[1];

        // 检查是否指定了分支：github.com/user/repo/tree/branch
        var branch = "main";
        if (parts.Length >= 4 && parts[2] == "tree")
            branch = parts[3];

        return $"https://raw.githubusercontent.com/{user}/{repo}/{branch}/repo.json";
    }

    public bool AddRepo(string name, string url)
    {
        var normalizedUrl = NormalizeRepoUrl(url);
        var repos = LoadRepos();
        if (repos.Any(r => r.Url == normalizedUrl)) return false;
        var repoName = string.IsNullOrWhiteSpace(name) ? normalizedUrl : name;
        repos.Add(new ScriptRepo { Name = repoName, Url = normalizedUrl });
        SaveRepos(repos);
        return true;
    }

    public void RemoveRepo(string url)
    {
        var repos = LoadRepos().Where(r => r.Url != url).ToList();
        SaveRepos(repos);
    }

    public async Task<List<RepoScriptInfo>> FetchRepoScriptsAsync(ScriptRepo repo,
        CancellationToken ct = default)
    {
        try
        {
            var json = await _http.GetStringAsync(repo.Url, ct);
            var index = JsonSerializer.Deserialize<RepoIndex>(json, _json);
            if (index == null) return [];

            var installed = GetInstalledScripts().ToDictionary(s => s.Id, s => s.Version);
            foreach (var s in index.Scripts)
            {
                if (installed.TryGetValue(s.Id, out var v))
                    s.InstalledVersion = v;
            }
            return index.Scripts;
        }
        catch (Exception e)
        {
            _logger.LogError(e, "拉取仓库 {Url} 失败", repo.Url);
            return [];
        }
    }

    public List<ScriptManifest> GetInstalledScripts()
    {
        var result = new List<ScriptManifest>();
        if (!Directory.Exists(ScriptsDir)) return result;

        foreach (var dir in Directory.GetDirectories(ScriptsDir))
        {
            var manifestPath = Path.Combine(dir, "manifest.json");
            if (!File.Exists(manifestPath)) continue;
            try
            {
                var json = File.ReadAllText(manifestPath);
                var m = JsonSerializer.Deserialize<ScriptManifest>(json, _json);
                if (m == null) continue;
                // 加载 settings.json -> LoadedParams
                var settingsPath = Path.Combine(dir, "settings.json");
                if (File.Exists(settingsPath))
                {
                    try
                    {
                        var defs = JsonSerializer.Deserialize<List<ScriptParamDef>>(
                            File.ReadAllText(settingsPath), _json);
                        if (defs != null) m.LoadedParams.AddRange(defs);
                    }
                    catch { /* 忽略解析失败 */ }
                }
                result.Add(m);
            }
            catch (Exception e)
            {
                _logger.LogWarning(e, "读取 manifest 失败: {Dir}", dir);
            }
        }
        return result;
    }

    public string GetScriptDir(string scriptId) => Path.Combine(ScriptsDir, scriptId);

    /// <summary>
    /// 下载并安装脚本。
    /// download_url 是整个仓库的 archive zip，repo_path 指定脚本在 zip 中的子目录。
    /// </summary>
    public async Task<bool> DownloadAndInstallAsync(RepoScriptInfo info,
        IProgress<(int Percent, string Message)>? progress = null,
        CancellationToken ct = default)
    {
        if (string.IsNullOrEmpty(info.DownloadUrl))
        {
            _logger.LogError("脚本 {Id} 没有下载地址", info.Id);
            return false;
        }

        var scriptDir = GetScriptDir(info.Id);
        var tmpZip = Path.Combine(AppDataDir, $"_tmp_repo_{info.Id}.zip");

        try
        {
            progress?.Report((0, $"正在下载 {info.Name}..."));

            // 下载整个仓库 zip
            using var resp = await _http.GetAsync(info.DownloadUrl,
                HttpCompletionOption.ResponseHeadersRead, ct);
            resp.EnsureSuccessStatusCode();

            var total = resp.Content.Headers.ContentLength ?? 0;
            await using var stream = await resp.Content.ReadAsStreamAsync(ct);
            await using var file = File.Create(tmpZip);

            var buffer = new byte[65536];
            long downloaded = 0;
            int read;
            while ((read = await stream.ReadAsync(buffer, ct)) > 0)
            {
                await file.WriteAsync(buffer.AsMemory(0, read), ct);
                downloaded += read;
                if (total > 0)
                    progress?.Report(((int)(downloaded * 75 / total),
                        $"下载中 {downloaded / 1024}KB / {total / 1024}KB"));
            }
            file.Close();

            progress?.Report((75, "正在解压..."));

            // zip 内的脚本路径：{repo}-{branch}/{repo_path}/
            // 例如：sra-scripts-main/repo/example_script/
            var repoPath = info.RepoPath; // 如 "repo/example_script"

            if (Directory.Exists(scriptDir))
                Directory.Delete(scriptDir, true);
            Directory.CreateDirectory(scriptDir);

            using var zip = ZipFile.OpenRead(tmpZip);

            // 找到 zip 内的顶层目录（如 sra-scripts-main）
            var topDir = zip.Entries.FirstOrDefault()?.FullName.Split('/')[0] ?? "";
            // 脚本在 zip 内的前缀
            var scriptPrefix = string.IsNullOrEmpty(repoPath)
                ? $"{topDir}/repo/{info.Id}/"
                : $"{topDir}/{repoPath.TrimStart('/')}/";

            var extracted = 0;
            foreach (var entry in zip.Entries)
            {
                if (!entry.FullName.StartsWith(scriptPrefix)) continue;
                var rel = entry.FullName[scriptPrefix.Length..];
                if (string.IsNullOrEmpty(rel)) continue;
                var target = Path.Combine(scriptDir, rel);
                if (entry.FullName.EndsWith("/"))
                    Directory.CreateDirectory(target);
                else
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                    entry.ExtractToFile(target, overwrite: true);
                    extracted++;
                }
            }

            if (extracted == 0)
            {
                _logger.LogError("脚本 {Id} 在 zip 中未找到文件（prefix: {Prefix}）", info.Id, scriptPrefix);
                if (Directory.Exists(scriptDir)) Directory.Delete(scriptDir, true);
                return false;
            }

            progress?.Report((100, $"安装完成（{extracted} 个文件）"));
            _logger.LogInformation("脚本 {Id} 安装成功，{Count} 个文件", info.Id, extracted);
            return true;
        }
        catch (Exception e)
        {
            _logger.LogError(e, "安装脚本 {Id} 失败", info.Id);
            if (Directory.Exists(scriptDir))
                Directory.Delete(scriptDir, true);
            return false;
        }
        finally
        {
            if (File.Exists(tmpZip)) File.Delete(tmpZip);
        }
    }

    public bool Uninstall(string scriptId)
    {
        var dir = GetScriptDir(scriptId);
        if (!Directory.Exists(dir)) return false;
        Directory.Delete(dir, true);
        _logger.LogInformation("脚本 {Id} 已卸载", scriptId);
        return true;
    }
}

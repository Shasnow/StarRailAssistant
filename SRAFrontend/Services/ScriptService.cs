using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Net.Http;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using SRAFrontend.Data;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

/// <summary>
/// 脚本仓库服务：负责仓库管理、脚本列表拉取、下载安装、本地扫描
/// </summary>
public class ScriptService
{
    private static readonly string ScriptsDir =
        Path.Combine(PathString.AppDataSraDir, "scripts");
    private static readonly string ReposConfigPath =
        Path.Combine(PathString.AppDataSraDir, "script_repos.json");

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNameCaseInsensitive = true,
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    private readonly IHttpClientFactory _httpClientFactory;

    public ScriptService(IHttpClientFactory httpClientFactory)
    {
        _httpClientFactory = httpClientFactory;
        Directory.CreateDirectory(ScriptsDir);
    }

    // ===== 仓库管理 =====

    public List<ScriptRepo> LoadRepos()
    {
        if (!File.Exists(ReposConfigPath)) return [];
        try
        {
            var json = File.ReadAllText(ReposConfigPath);
            var root = JsonSerializer.Deserialize<ReposConfig>(json, JsonOpts);
            return root?.Repos ?? [];
        }
        catch { return []; }
    }

    private void SaveRepos(List<ScriptRepo> repos)
    {
        var json = JsonSerializer.Serialize(new ReposConfig { Repos = repos }, JsonOpts);
        File.WriteAllText(ReposConfigPath, json);
    }

    public bool AddRepo(string name, string url)
    {
        var repos = LoadRepos();
        if (repos.Exists(r => r.Url == url)) return false;
        repos.Add(new ScriptRepo { Name = name, Url = url });
        SaveRepos(repos);
        return true;
    }

    public void RemoveRepo(string url)
    {
        var repos = LoadRepos();
        repos.RemoveAll(r => r.Url == url);
        SaveRepos(repos);
    }

    // ===== 远程脚本列表 =====

    public async Task<List<RepoScriptInfo>> FetchRepoScriptsAsync(ScriptRepo repo)
    {
        var client = _httpClientFactory.CreateClient("GlobalClient");
        var json = await client.GetStringAsync(repo.Url);
        var root = JsonSerializer.Deserialize<RepoIndex>(json, JsonOpts);
        if (root?.Scripts == null) return [];

        var installed = GetInstalledScripts();
        var installedMap = new Dictionary<string, string>();
        foreach (var s in installed) installedMap[s.Id] = s.Version;

        var result = new List<RepoScriptInfo>();
        foreach (var item in root.Scripts)
        {
            var info = new RepoScriptInfo
            {
                Id = item.Id ?? "",
                Name = item.Name ?? "",
                Version = item.Version ?? "0.0.0",
                Description = item.Description ?? "",
                Author = item.Author ?? "",
                LastUpdated = item.LastUpdated ?? "",
                DownloadUrl = item.DownloadUrl ?? "",
            };
            if (installedMap.TryGetValue(info.Id, out var ver))
            {
                info.InstalledVersion = ver;
                info.HasUpdate = info.Version != ver;
            }
            result.Add(info);
        }
        return result;
    }

    // ===== 本地脚本 =====

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
                var m = JsonSerializer.Deserialize<ManifestJson>(json, JsonOpts);
                if (m == null) continue;
                var manifest = new ScriptManifest
                {
                    Id = m.Id ?? Path.GetFileName(dir),
                    Name = m.Name ?? "",
                    Version = m.Version ?? "0.0.0",
                    Description = m.Description ?? "",
                    Author = m.Author ?? "",
                };
                foreach (var t in m.Tasks ?? [])
                    manifest.Tasks.Add(new ScriptTaskDef
                    {
                        Name = t.Name ?? "",
                        Entry = t.Entry ?? "",
                        Class = t.Class ?? "",
                    });
                // 加载 settings.json -> LoadedParams
                var settingsPath = Path.Combine(dir, "settings.json");
                if (File.Exists(settingsPath))
                {
                    try
                    {
                        var settingsJson = File.ReadAllText(settingsPath);
                        var defs = System.Text.Json.JsonSerializer.Deserialize<List<ScriptParamDef>>(
                            settingsJson, JsonOpts);
                        if (defs != null) manifest.LoadedParams.AddRange(defs);
                    }
                    catch { /* 忽略解析失败 */ }
                }
                result.Add(manifest);
            }
            catch { /* 跳过损坏的 manifest */ }
        }
        return result;
    }

    public string GetScriptDir(string scriptId) =>
        Path.Combine(ScriptsDir, scriptId);

    /// <summary>读取脚本目录下 settings.json，解析为参数定义列表</summary>
    public List<ScriptParamDef> LoadScriptParamDefs(string scriptId)
    {
        var path = Path.Combine(ScriptsDir, scriptId, "settings.json");
        if (!File.Exists(path)) return [];
        try
        {
            var json = File.ReadAllText(path);
            return JsonSerializer.Deserialize<List<ScriptParamDef>>(json, JsonOpts) ?? [];
        }
        catch { return []; }
    }

    /// <summary>读取已安装脚本的本地 README.md</summary>
    public string? ReadLocalReadme(string scriptId)
    {
        var path = Path.Combine(ScriptsDir, scriptId, "README.md");
        return File.Exists(path) ? File.ReadAllText(path) : null;
    }

    /// <summary>从仓库远程拉取 README（通过 repo_path 构造 raw URL）</summary>
    public Task<string?> FetchReadmeAsync(RepoScriptInfo info)
    {
        if (string.IsNullOrEmpty(info.DownloadUrl)) return Task.FromResult<string?>(null);
        // download_url 形如 https://github.com/xxx/sra-scripts/archive/refs/heads/main.zip
        // 尝试先看本地已安装
        var local = ReadLocalReadme(info.Id);
        if (local != null) return Task.FromResult<string?>(local);

        // 如果未安装，从 GitHub raw 拉取（download_url 转换为 raw 地址）
        // 由于 download_url 是 zip，只能提示用户安装后查看
        return Task.FromResult<string?>("_请先安装脚本以查看本地 README，或访问仓库主页查阅文档。_");
    }

    // ===== 下载安装 =====

    public async Task<bool> DownloadAndInstallAsync(
        RepoScriptInfo info,
        IProgress<(int Percent, string Message)>? progress = null)
    {
        if (string.IsNullOrEmpty(info.DownloadUrl)) return false;

        var scriptDir = GetScriptDir(info.Id);
        var tmpZip = Path.Combine(PathString.AppDataSraDir, $"_tmp_{info.Id}.zip");

        try
        {
            progress?.Report((0, $"正在下载 {info.Name}..."));
            var client = _httpClientFactory.CreateClient("GlobalClient");

            using var resp = await client.GetAsync(
                info.DownloadUrl, HttpCompletionOption.ResponseHeadersRead);
            resp.EnsureSuccessStatusCode();

            var total = resp.Content.Headers.ContentLength ?? 0;
            await using var stream = await resp.Content.ReadAsStreamAsync();
            await using var file = File.Create(tmpZip);

            var buffer = new byte[8192];
            long downloaded = 0;
            int read;
            while ((read = await stream.ReadAsync(buffer)) > 0)
            {
                await file.WriteAsync(buffer.AsMemory(0, read));
                downloaded += read;
                if (total > 0)
                    progress?.Report(((int)(downloaded * 80 / total),
                        $"下载中 {downloaded / 1024}KB / {total / 1024}KB"));
            }

            progress?.Report((80, "正在解压..."));

            if (Directory.Exists(scriptDir))
                Directory.Delete(scriptDir, true);
            Directory.CreateDirectory(scriptDir);

            ExtractZipStrippingTopDir(tmpZip, scriptDir, info.Id);

            progress?.Report((100, "安装完成"));
            return true;
        }
        catch
        {
            if (Directory.Exists(scriptDir))
                Directory.Delete(scriptDir, true);
            return false;
        }
        finally
        {
            if (File.Exists(tmpZip)) File.Delete(tmpZip);
        }
    }

    private static void ExtractZipStrippingTopDir(string zipPath, string destDir, string scriptId)
    {
        using var archive = ZipFile.OpenRead(zipPath);
        // 找到脚本子目录前缀：zip 内路径形如 sra-scripts-main/repo/divergent_universe/...
        var prefix = "";
        foreach (var entry in archive.Entries)
        {
            var parts = entry.FullName.Split('/');
            // 寻找第一个包含 scriptId 的目录层级
            for (var i = 0; i < parts.Length - 1; i++)
            {
                if (!parts[i].Equals(scriptId, StringComparison.OrdinalIgnoreCase)) continue;
                // parts[0..i] 是要剥离的前缀
                prefix = string.Join("/", parts[..( i + 1)]) + "/";
                break;
            }
            if (!string.IsNullOrEmpty(prefix)) break;
        }

        foreach (var entry in archive.Entries)
        {
            if (!entry.FullName.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) continue;
            var relative = entry.FullName[prefix.Length..];
            if (string.IsNullOrEmpty(relative)) continue;

            var target = Path.Combine(destDir, relative.Replace('/', Path.DirectorySeparatorChar));
            if (entry.FullName.EndsWith('/'))
            {
                Directory.CreateDirectory(target);
            }
            else
            {
                Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                entry.ExtractToFile(target, overwrite: true);
            }
        }
    }

    public bool Uninstall(string scriptId)
    {
        var dir = GetScriptDir(scriptId);
        if (!Directory.Exists(dir)) return false;
        Directory.Delete(dir, true);
        return true;
    }

    // ===== 内部 JSON 映射类 =====

    private class ReposConfig
    {
        [JsonPropertyName("repos")]
        public List<ScriptRepo> Repos { get; set; } = [];
    }

    private class RepoIndex
    {
        [JsonPropertyName("scripts")]
        public List<RepoScriptJson>? Scripts { get; set; }
    }

    private class RepoScriptJson
    {
        [JsonPropertyName("id")]          public string? Id { get; set; }
        [JsonPropertyName("name")]        public string? Name { get; set; }
        [JsonPropertyName("version")]     public string? Version { get; set; }
        [JsonPropertyName("description")] public string? Description { get; set; }
        [JsonPropertyName("author")]      public string? Author { get; set; }
        [JsonPropertyName("last_updated")]public string? LastUpdated { get; set; }
        [JsonPropertyName("download_url")]public string? DownloadUrl { get; set; }
    }

    private class ManifestJson
    {
        [JsonPropertyName("id")]          public string? Id { get; set; }
        [JsonPropertyName("name")]        public string? Name { get; set; }
        [JsonPropertyName("version")]     public string? Version { get; set; }
        [JsonPropertyName("description")] public string? Description { get; set; }
        [JsonPropertyName("author")]      public string? Author { get; set; }
        [JsonPropertyName("tasks")]       public List<TaskJson>? Tasks { get; set; }
    }

    private class TaskJson
    {
        [JsonPropertyName("name")]  public string? Name { get; set; }
        [JsonPropertyName("entry")] public string? Entry { get; set; }
        [JsonPropertyName("class")] public string? Class { get; set; }
    }
}

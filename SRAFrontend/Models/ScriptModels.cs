using System.Collections.Generic;

namespace SRAFrontend.Models;

/// <summary>脚本仓库配置</summary>
public class ScriptRepo
{
    public string Name { get; set; } = "";
    public string Url { get; set; } = "";
    public bool Enabled { get; set; } = true;
}

/// <summary>脚本 manifest.json 中的单个任务定义</summary>
public class ScriptTaskDef
{
    public string Name { get; set; } = "";
    public string Entry { get; set; } = "";   // .py 文件名
    public string Class { get; set; } = "";   // 类名
}

/// <summary>脚本 manifest.json</summary>
public class ScriptManifest
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public string Version { get; set; } = "0.0.0";
    public string Description { get; set; } = "";
    public string Author { get; set; } = "";
    public List<ScriptTaskDef> Tasks { get; set; } = [];
}

/// <summary>仓库 repo.json 中的脚本条目（含安装状态）</summary>
public class RepoScriptInfo
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public string Version { get; set; } = "0.0.0";
    public string Description { get; set; } = "";
    public string Author { get; set; } = "";
    public string DownloadUrl { get; set; } = "";
    public string RepoPath { get; set; } = "";       // 脚本在仓库 zip 中的子目录路径
    public string LastUpdated { get; set; } = "";
    public List<ScriptTaskDef> Tasks { get; set; } = [];
    // 由前端填充
    public string? InstalledVersion { get; set; }
    public bool HasUpdate => InstalledVersion != null && InstalledVersion != Version;
    public bool IsInstalled => InstalledVersion != null;
}

/// <summary>仓库 repo.json 根结构</summary>
public class RepoIndex
{
    public string Name { get; set; } = "";
    public string Version { get; set; } = "";
    public List<RepoScriptInfo> Scripts { get; set; } = [];
}

/// <summary>仓库配置文件根结构</summary>
public class ScriptReposConfig
{
    public List<ScriptRepo> Repos { get; set; } = [];
}

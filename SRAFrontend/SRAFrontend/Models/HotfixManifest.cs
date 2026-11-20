using System.Collections.Generic;

namespace SRAFrontend.Models;

/// <summary>
/// patch 级热更新差量清单（由 scripts/package.py 生成，文档站 / R2 托管）。
/// </summary>
public class HotfixManifest
{
    /// <summary>清单格式版本</summary>
    public int Schema { get; init; } = 1;

    /// <summary>发布通道，目前仅 stable 会产生清单</summary>
    public string Channel { get; init; } = "stable";

    /// <summary>清单对应的 patch 版本（无 v 前缀）</summary>
    public string Version { get; init; } = "";

    /// <summary>同一 minor 系列的基线版本（x.y.0）</summary>
    public string BaseVersion { get; init; } = "";

    /// <summary>清单生成时间（ISO 8601）</summary>
    public string GeneratedAt { get; init; } = "";

    /// <summary>单文件下载 URL 模板，支持 {version} / {path} 占位符</summary>
    public List<string> Sources { get; init; } = [];

    /// <summary>新增或修改的文件</summary>
    public List<HotfixFile> Files { get; init; } = [];

    /// <summary>相对基线版本被删除的文件</summary>
    public List<string> Deleted { get; init; } = [];
}

/// <summary>热更新清单中的单个文件条目。</summary>
public class HotfixFile
{
    /// <summary>相对应用根目录的路径（正斜杠分隔）</summary>
    public string Path { get; init; } = "";

    /// <summary>文件 SHA-256（小写十六进制）</summary>
    public string Sha256 { get; init; } = "";

    /// <summary>文件字节数</summary>
    public long Size { get; init; }
}

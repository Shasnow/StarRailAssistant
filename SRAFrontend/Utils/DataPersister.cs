using System;
using System.IO;
using System.Text.Json;
using Serilog;
using SRAFrontend.Data;
using SRAFrontend.Models;

namespace SRAFrontend.Utils;

public static class DataPersister
{
    private static readonly JsonSerializerOptions JsonSerializerOptions = new()
    {
        WriteIndented = true
    };

    /// <summary>
    ///     原子写入文件：先写临时文件，再替换目标文件。
    ///     写入过程中崩溃不会损坏原文件。
    /// </summary>
    private static void SafeWriteAllText(string path, string content)
    {
        var dir = Path.GetDirectoryName(path)!;
        var tempPath = Path.Combine(dir, Path.GetRandomFileName());
        try
        {
            File.WriteAllText(tempPath, content);
            if (File.Exists(path))
            {
                File.Replace(tempPath, path, null);
            }
            else
            {
                File.Move(tempPath, path);
            }
        }
        catch
        {
            if (File.Exists(tempPath)) File.Delete(tempPath);
            throw;
        }
    }

    #region Cache

    public static Cache LoadCache()
    {
        try
        {
            if (!File.Exists(PathString.CacheJson)) return new Cache();
            var json = File.ReadAllText(PathString.CacheJson);
            if (string.IsNullOrWhiteSpace(json)) return new Cache();
            return JsonSerializer.Deserialize<Cache>(json) ?? new Cache();
        }
        catch (Exception e)
        {
            Log.Error(e, "Error loading cache. using empty cache");
            return new Cache();
        }
    }

    public static void SaveCache(Cache cache)
    {
        var json = JsonSerializer.Serialize(cache, JsonSerializerOptions);
        SafeWriteAllText(PathString.CacheJson, json);
    }

    #endregion
}

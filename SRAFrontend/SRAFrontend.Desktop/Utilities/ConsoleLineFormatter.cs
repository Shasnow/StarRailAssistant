using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.RegularExpressions;
using Avalonia.Controls.Documents;
using Avalonia.Media;

namespace SRAFrontend.Desktop.Utilities;

/// <summary>控制台日志片段的语义类别</summary>
public enum ConsoleSegmentKind
{
    Text, // 普通文本
    Dim, // 时间戳等弱化信息
    Trace,
    Debug,
    Info,
    Warn,
    Error,
    Success,
    JsonKey,
    JsonString,
    JsonNumber,
    JsonBool,
    JsonPunct
}

/// <summary>控制台单行中的一个着色片段</summary>
public readonly record struct ConsoleSegment(string Text, ConsoleSegmentKind Kind);

/// <summary>
///     控制台日志着色与 JSON 美化：
///     按日志级别（TRACE/DEBUG/INFO/WARN/ERROR…）与时间戳着色；
///     以 { 或 [ 开头且可解析的行按 JSON 缩进排版，并按语法元素（键/字符串/数字/布尔/标点）着色。
///     片段解析结果按原始行缓存，重复行不重复解析。
/// </summary>
public static class ConsoleLineFormatter
{
    private const int MaxCacheEntries = 4000;

    private static readonly ConcurrentDictionary<string, IReadOnlyList<ConsoleSegment>> Cache = new();

    /// <summary>JSON 显示用序列化选项：不转义非 ASCII 字符，中日韩文本按原文显示</summary>
    private static readonly JsonSerializerOptions DisplayJsonOptions = new()
    {
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    private static readonly Regex TimeRegex = new(@"\b\d{1,2}:\d{2}:\d{2}(?:\.\d+)?\b", RegexOptions.Compiled);

    private static readonly Regex LevelRegex =
        new(@"\b(SUCCESS|WARNING|FATAL|TRACE|DEBUG|ERROR|INFO|WARN|DBG|INF|WRN|ERR)\b",
            RegexOptions.Compiled);

    // 深色背景下的多色配色（VSCode Dark+ / One Dark 风格）
    private static readonly IReadOnlyDictionary<ConsoleSegmentKind, SolidColorBrush> Palette =
        new Dictionary<ConsoleSegmentKind, SolidColorBrush>
        {
            [ConsoleSegmentKind.Text] = new SolidColorBrush(Color.Parse("#D4D4D4")),
            [ConsoleSegmentKind.Dim] = new SolidColorBrush(Color.Parse("#80868B")),
            [ConsoleSegmentKind.Trace] = new SolidColorBrush(Color.Parse("#6E7681")),
            [ConsoleSegmentKind.Debug] = new SolidColorBrush(Color.Parse("#61AFEF")),
            [ConsoleSegmentKind.Info] = new SolidColorBrush(Color.Parse("#98C379")),
            [ConsoleSegmentKind.Warn] = new SolidColorBrush(Color.Parse("#E5C07B")),
            [ConsoleSegmentKind.Error] = new SolidColorBrush(Color.Parse("#E06C75")),
            [ConsoleSegmentKind.Success] = new SolidColorBrush(Color.Parse("#23D18B")),
            [ConsoleSegmentKind.JsonKey] = new SolidColorBrush(Color.Parse("#9CDCFE")),
            [ConsoleSegmentKind.JsonString] = new SolidColorBrush(Color.Parse("#CE9178")),
            [ConsoleSegmentKind.JsonNumber] = new SolidColorBrush(Color.Parse("#B5CEA8")),
            [ConsoleSegmentKind.JsonBool] = new SolidColorBrush(Color.Parse("#569CD6")),
            [ConsoleSegmentKind.JsonPunct] = new SolidColorBrush(Color.Parse("#7F848C"))
        };

    /// <summary>把若干原始日志行渲染为可直接赋给 TextBlock.Inlines 的行内集合</summary>
    public static InlineCollection BuildInlines(IEnumerable<string> lines)
    {
        var inlines = new InlineCollection();
        var first = true;
        foreach (var line in lines)
        {
            if (!first) inlines.Add(new LineBreak());
            first = false;
            foreach (var segment in FormatLine(line))
            {
                // 片段内显式换行，不依赖 Run 文本中 \n 的渲染行为
                var parts = segment.Text.Split('\n');
                for (var i = 0; i < parts.Length; i++)
                {
                    if (i > 0) inlines.Add(new LineBreak());
                    if (parts[i].Length == 0) continue;
                    inlines.Add(new Run { Text = parts[i], Foreground = Palette[segment.Kind] });
                }
            }
        }

        return inlines;
    }

    /// <summary>解析单行日志为着色片段（带缓存）</summary>
    public static IReadOnlyList<ConsoleSegment> FormatLine(string line)
    {
        if (string.IsNullOrEmpty(line)) return [new ConsoleSegment(string.Empty, ConsoleSegmentKind.Text)];
        if (Cache.TryGetValue(line, out var cached)) return cached;

        var computed = Compute(line);
        if (Cache.Count > MaxCacheEntries) Cache.Clear();
        Cache[line] = computed;
        return computed;
    }

    private static IReadOnlyList<ConsoleSegment> Compute(string line)
    {
        var trimmed = line.Trim();
        if (trimmed.Length > 0 && trimmed[0] is '{' or '[' && TryFormatJson(trimmed, out var jsonSegments))
            return jsonSegments;
        return FormatPlain(line);
    }

    /// <summary>普通行：时间戳弱化，日志级别着色</summary>
    private static IReadOnlyList<ConsoleSegment> FormatPlain(string line)
    {
        var segments = new List<ConsoleSegment>(4);
        var pos = 0;
        var time = TimeRegex.Match(line);
        var level = LevelRegex.Match(line);

        // 级别标记出现在时间戳之前（或没有时间戳）时，先处理级别
        if (level.Success && (!time.Success || level.Index < time.Index))
        {
            AddSegment(segments, line[pos..level.Index], ConsoleSegmentKind.Text);
            AddSegment(segments, level.Value, KindForLevel(level.Value));
            pos = level.Index + level.Length;
            time = TimeRegex.Match(line, pos);
        }

        if (time.Success)
        {
            AddSegment(segments, line[pos..time.Index], ConsoleSegmentKind.Text);
            AddSegment(segments, time.Value, ConsoleSegmentKind.Dim);
            pos = time.Index + time.Length;

            level = LevelRegex.Match(line, pos);
            if (level.Success)
            {
                AddSegment(segments, line[pos..level.Index], ConsoleSegmentKind.Text);
                AddSegment(segments, level.Value, KindForLevel(level.Value));
                pos = level.Index + level.Length;
            }
        }

        AddSegment(segments, line[pos..], ConsoleSegmentKind.Text);
        return segments;
    }

    private static ConsoleSegmentKind KindForLevel(string token)
    {
        return token switch
        {
            "SUCCESS" => ConsoleSegmentKind.Success,
            "TRACE" => ConsoleSegmentKind.Trace,
            "DEBUG" or "DBG" => ConsoleSegmentKind.Debug,
            "WARN" or "WARNING" or "WRN" => ConsoleSegmentKind.Warn,
            "ERROR" or "FATAL" or "ERR" => ConsoleSegmentKind.Error,
            _ => ConsoleSegmentKind.Info // INFO / INF
        };
    }

    /// <summary>JSON 行：两空格缩进排版，按语法元素着色；解析失败返回 false 走普通着色</summary>
    private static bool TryFormatJson(string text, out List<ConsoleSegment> segments)
    {
        segments = new List<ConsoleSegment>(32);
        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(text);
        }
        catch (JsonException)
        {
            segments.Clear();
            return false;
        }

        using (doc)
        {
            WriteElement(doc.RootElement, 0, segments);
            return true;
        }
    }

    private static void WriteElement(JsonElement element, int depth, List<ConsoleSegment> segments)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
            {
                AddSegment(segments, "{", ConsoleSegmentKind.JsonPunct);
                var count = 0;
                foreach (var property in element.EnumerateObject())
                {
                    if (count++ > 0) AddSegment(segments, ",", ConsoleSegmentKind.JsonPunct);
                    AddSegment(segments, "\n" + new string(' ', (depth + 1) * 2), ConsoleSegmentKind.JsonPunct);
                    AddSegment(segments, JsonSerializer.Serialize(property.Name, DisplayJsonOptions),
                        ConsoleSegmentKind.JsonKey);
                    AddSegment(segments, ": ", ConsoleSegmentKind.JsonPunct);
                    WriteElement(property.Value, depth + 1, segments);
                }

                if (count > 0) AddSegment(segments, "\n" + new string(' ', depth * 2), ConsoleSegmentKind.JsonPunct);
                AddSegment(segments, "}", ConsoleSegmentKind.JsonPunct);
                break;
            }
            case JsonValueKind.Array:
            {
                AddSegment(segments, "[", ConsoleSegmentKind.JsonPunct);
                for (var i = 0; i < element.GetArrayLength(); i++)
                {
                    if (i > 0) AddSegment(segments, ",", ConsoleSegmentKind.JsonPunct);
                    AddSegment(segments, "\n" + new string(' ', (depth + 1) * 2), ConsoleSegmentKind.JsonPunct);
                    WriteElement(element[i], depth + 1, segments);
                }

                if (element.GetArrayLength() > 0)
                    AddSegment(segments, "\n" + new string(' ', depth * 2), ConsoleSegmentKind.JsonPunct);
                AddSegment(segments, "]", ConsoleSegmentKind.JsonPunct);
                break;
            }
            case JsonValueKind.String:
                // 解码后重新加引号，避免把后端的 \uXXXX 转义原样显示
                AddSegment(segments, JsonSerializer.Serialize(element.GetString(), DisplayJsonOptions),
                    ConsoleSegmentKind.JsonString);
                break;
            case JsonValueKind.Number:
                AddSegment(segments, element.GetRawText(), ConsoleSegmentKind.JsonNumber);
                break;
            case JsonValueKind.True:
            case JsonValueKind.False:
            case JsonValueKind.Null:
                AddSegment(segments, element.GetRawText(), ConsoleSegmentKind.JsonBool);
                break;
            default:
                AddSegment(segments, element.GetRawText(), ConsoleSegmentKind.Text);
                break;
        }
    }

    /// <summary>追加片段并与相邻同类别片段合并，减少 Run 数量</summary>
    private static void AddSegment(List<ConsoleSegment> segments, string text, ConsoleSegmentKind kind)
    {
        if (string.IsNullOrEmpty(text)) return;
        if (segments.Count > 0 && segments[^1].Kind == kind)
            segments[^1] = segments[^1] with { Text = segments[^1].Text + text };
        else
            segments.Add(new ConsoleSegment(text, kind));
    }
}

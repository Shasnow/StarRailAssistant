using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using System.Threading.Channels;
using SRAFrontend.Data;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Services;

/// <summary>
/// Fan-outs backend logs to HTTP clients and keeps a small in-memory backlog.
/// </summary>
/// <remarks>
/// Logs can come from two places: direct output of the CLI process owned by this
/// server, and the latest backend log file for tasks started by SRA.exe.  Tailing
/// the file keeps WebUI useful when the user starts a task on the desktop and
/// later opens a phone browser to watch or stop it.
/// </remarks>
public sealed class LogStreamService : IDisposable
{
    private readonly ConcurrentBag<WeakReference<Channel<string>>> _subscribers = [];
    private readonly List<string> _recentLogs = [];
    private readonly Lock _lock = new();
    private readonly CancellationTokenSource _fileTailCts = new();
    private string? _tailedFile;
    private long _tailPosition;
    private const int MaxRecentLogs = 500;

    public LogStreamService(IBackendService backendService)
    {
        backendService.Outputted += Push;
        _ = Task.Run(() => TailBackendLogAsync(_fileTailCts.Token));
    }

    private void Push(string line)
    {
        lock (_lock)
        {
            // Avoid duplicate adjacent lines because file tailing and direct
            // process output may briefly report the same backend line.
            if (_recentLogs.Count == 0 || _recentLogs[^1] != line)
                _recentLogs.Add(line);
            if (_recentLogs.Count > MaxRecentLogs)
                _recentLogs.RemoveAt(0);
        }

        var dead = new List<WeakReference<Channel<string>>>();
        foreach (var weakRef in _subscribers)
        {
            if (weakRef.TryGetTarget(out var channel))
                channel.Writer.TryWrite(line);
            else
                dead.Add(weakRef);
        }

        foreach (var ignored in dead)
        {
            _ = ignored;
            _subscribers.TryTake(out var removed);
        }
    }

    public List<string> GetRecentLogs(int count = 100)
    {
        lock (_lock)
        {
            return _recentLogs.TakeLast(Math.Min(count, _recentLogs.Count)).ToList();
        }
    }

    public async IAsyncEnumerable<string> Subscribe(
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var channel = Channel.CreateUnbounded<string>(
            new UnboundedChannelOptions { SingleWriter = true });

        // Weak references prevent abandoned SSE clients from keeping channels
        // alive forever if a browser disconnect is not observed immediately.
        _subscribers.Add(new WeakReference<Channel<string>>(channel));

        await foreach (var line in channel.Reader.ReadAllAsync(cancellationToken))
            yield return line;
    }

    private async Task TailBackendLogAsync(CancellationToken cancellationToken)
    {
        while (!cancellationToken.IsCancellationRequested)
        {
            try
            {
                var file = GetLatestBackendLogFile();
                if (file is not null)
                {
                    if (!string.Equals(_tailedFile, file.FullName, StringComparison.OrdinalIgnoreCase))
                    {
                        _tailedFile = file.FullName;
                        // Start at EOF for a new file; historical lines are
                        // served by /Task/logs, while SSE should stream fresh
                        // lines after the browser connects.
                        _tailPosition = Math.Max(0, file.Length);
                    }

                    await ReadNewLinesAsync(file.FullName, cancellationToken);
                }
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch
            {
                // Best-effort log tailing. Direct backend process output is still streamed.
            }

            await Task.Delay(1000, cancellationToken);
        }
    }

    private async Task ReadNewLinesAsync(string path, CancellationToken cancellationToken)
    {
        await using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        if (_tailPosition > stream.Length)
            _tailPosition = 0;

        stream.Seek(_tailPosition, SeekOrigin.Begin);
        using var reader = new StreamReader(stream);
        while (await reader.ReadLineAsync(cancellationToken) is { } line)
        {
            if (!string.IsNullOrEmpty(line))
                Push(line);
        }
        _tailPosition = stream.Position;
    }

    private static FileInfo? GetLatestBackendLogFile()
    {
        if (!Directory.Exists(DataPath.BackendLogsDir))
            return null;
        return Directory.GetFiles(DataPath.BackendLogsDir, "SRA*.log")
            .Select(path => new FileInfo(path))
            .OrderByDescending(info => info.LastWriteTimeUtc)
            .FirstOrDefault();
    }

    public void Dispose()
    {
        _fileTailCts.Cancel();
        _fileTailCts.Dispose();
    }
}

using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using System.Threading.Channels;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Services;

/// <summary>
/// 订阅后端日志，为 SSE 客户端提供异步流式读取。
/// </summary>
public sealed class LogStreamService : IDisposable
{
    private readonly ConcurrentBag<WeakReference<Channel<string>>> _subscribers = [];
    private readonly List<string> _recentLogs = [];
    private readonly Lock _lock = new();
    private const int MaxRecentLogs = 500;

    public LogStreamService(IBackendService backendService)
    {
        backendService.Outputted += OnOutput;
    }

    private void OnOutput(string line)
    {
        lock (_lock)
        {
            _recentLogs.Add(line);
            if (_recentLogs.Count > MaxRecentLogs)
                _recentLogs.RemoveAt(0);
        }

        // 广播给所有活跃的订阅者
        var dead = new List<WeakReference<Channel<string>>>();
        foreach (var weakRef in _subscribers)
        {
            if (weakRef.TryGetTarget(out var channel))
            {
                channel.Writer.TryWrite(line);
            }
            else
            {
                dead.Add(weakRef);
            }
        }

        // 清理已失效的订阅者
        foreach (var d in dead)
            _subscribers.TryTake(out _);
    }

    /// <summary>获取最近的日志条目</summary>
    public List<string> GetRecentLogs(int count = 100)
    {
        lock (_lock)
        {
            return _recentLogs.TakeLast(Math.Min(count, _recentLogs.Count)).ToList();
        }
    }

    /// <summary>订阅实时日志流</summary>
    public async IAsyncEnumerable<string> Subscribe(
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var channel = Channel.CreateUnbounded<string>(
            new UnboundedChannelOptions { SingleWriter = true });

        _subscribers.Add(new WeakReference<Channel<string>>(channel));

        await foreach (var line in channel.Reader.ReadAllAsync(cancellationToken))
        {
            yield return line;
        }
    }

    public void Dispose()
    {
        // WeakReference 会自然回收
    }
}

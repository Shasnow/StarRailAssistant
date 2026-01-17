using System;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace SRAFrontend.Services;

public class WebsocketService(ILogger<WebsocketService> logger) : IDisposable
{
    private CancellationTokenSource? _cts;
    private bool _isConnected;
    private bool _isDisposed;
    // 核心字段
    private ClientWebSocket? _webSocket;
    /// <summary>
    ///     当前连接状态
    /// </summary>
    public bool IsConnected => _isConnected && _webSocket?.State == WebSocketState.Open;

    // 事件：接收消息（供ViewModel订阅，输出到控制台）
    public event Action<string>? MessageReceived;

    // 事件：连接状态变更（供ViewModel更新状态）
    public event Action<bool>? ConnectionStateChanged;

    /// <summary>
    ///     启动WebSocket连接（异步）
    /// </summary>
    /// <param name="url">WebSocket地址（如 ws://localhost:8080 或 wss://xxx）</param>
    /// <param name="timeoutMs">连接超时（默认5000ms）</param>
    /// <returns>是否连接成功</returns>
    public async Task<bool> StartAsync(string url, int timeoutMs = 5000)
    {
        // 校验参数
        if (string.IsNullOrWhiteSpace(url))
        {
            logger.LogError("WebSocket URL is null or empty");
            OnMessageReceived("[错误] WebSocket连接地址不能为空");
            return false;
        }

        // 已连接则先断开
        if (IsConnected) await StopAsync();

        try
        {
            // 初始化WebSocket和取消令牌
            _webSocket = new ClientWebSocket();
            _cts = new CancellationTokenSource(TimeSpan.FromMilliseconds(timeoutMs));
            OnMessageReceived($"正在连接WebSocket服务器: {url}");

            // 发起连接
            await _webSocket.ConnectAsync(new Uri(url), _cts.Token);

            // 连接成功
            _isConnected = true;
            OnConnectionStateChanged(true);
            logger.LogInformation("WebSocket connected: {Url}", url);
            OnMessageReceived($"WebSocket连接成功: {url}");

            // 启动后台接收消息的循环（不阻塞主线程）
            _ = ReceiveMessagesLoopAsync();

            return true;
        }
        catch (OperationCanceledException)
        {
            logger.LogWarning("Connect timeout ({Timeout}ms): {Url}", timeoutMs, url);
            OnMessageReceived($"[错误] WebSocket连接超时（{timeoutMs}ms）: {url}");
        }
        catch (WebSocketException ex)
        {
            logger.LogError(ex, "Fail to connect: {Url}", url);
            OnMessageReceived($"[错误] WebSocket连接失败: {ex.Message}");
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Connect Error: {Url}", url);
            OnMessageReceived($"[错误] WebSocket连接异常: {ex.Message}");
        }

        // 连接失败清理资源
        CleanupResources();
        OnConnectionStateChanged(false);
        return false;
    }

    /// <summary>
    ///     停止WebSocket连接（异步）
    /// </summary>
    public async Task StopAsync()
    {
        if (!IsConnected)
        {
            return;
        }

        try
        {
            logger.LogInformation("Disconnecting WebSocket...");
            OnMessageReceived("正在断开WebSocket连接...");

            // 优雅关闭连接（发送关闭帧）
            if (_webSocket?.State == WebSocketState.Open)
                await _webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "客户端主动断开", CancellationToken.None);
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "WebSocket disconnect error");
            OnMessageReceived($"[警告] WebSocket断开异常: {ex.Message}");
        }
        finally
        {
            // 强制清理资源
            CleanupResources();
            _isConnected = false;
            OnConnectionStateChanged(false);
            logger.LogInformation("WebSocket disconnected");
            OnMessageReceived("WebSocket已断开连接");
        }
    }

    /// <summary>
    ///     发送消息到WebSocket服务器（异步）
    /// </summary>
    /// <param name="message">要发送的文本消息</param>
    /// <returns>是否发送成功</returns>
    public async Task<bool> SendAsync(string message)
    {
        // 校验状态和参数
        if (!IsConnected)
        {
            logger.LogWarning("Attempt to send message while WebSocket is not connected");
            OnMessageReceived("[错误] 无法发送消息：WebSocket未连接");
            return false;
        }

        if (string.IsNullOrWhiteSpace(message))
        {
            logger.LogWarning("Attempt to send empty message");
            OnMessageReceived("[警告] 发送的消息不能为空");
            return false;
        }

        try
        {
            var command = message.Split(' ')[0].ToLower();
            var args = message.Contains(' ') ? message[(command.Length + 1)..] : string.Empty;
            var formatMessage = new { command, args };
            var buffer = JsonSerializer.SerializeToUtf8Bytes(formatMessage);
            // 发送文本消息
            await _webSocket!.SendAsync(
                new ArraySegment<byte>(buffer),
                WebSocketMessageType.Text,
                true,
                CancellationToken.None);

            logger.LogInformation("Sent WebSocket message: {formatMessage}", formatMessage);
            OnMessageReceived($"[发送] {message}");
            return true;
        }
        catch (WebSocketException ex)
        {
            logger.LogError(ex, "WebSocket send message failed: {Message}", message);
            OnMessageReceived($"[错误] 发送消息失败: {ex.Message}");
            // 发送失败自动断开
            await StopAsync();
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "WebSocket send message failed: {Message}", message);
            OnMessageReceived($"[错误] 发送消息异常: {ex.Message}");
        }

        return false;
    }

    /// <summary>
    ///     后台接收消息循环（持续监听服务器消息）
    /// </summary>
    private async Task ReceiveMessagesLoopAsync()
    {
        if (_webSocket == null || !IsConnected) return;

        // 接收缓冲区（4KB，可根据需求调整）
        var buffer = new byte[4096];

        try
        {
            while (IsConnected)
            {
                // 接收消息（阻塞直到有消息/连接关闭）
                var result = await _webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);

                // 处理关闭帧
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    logger.LogInformation("Received WebSocket server close frame, status code: {Code}", result.CloseStatus);
                    OnMessageReceived($"[提示] 服务器断开连接: {result.CloseStatusDescription ?? "无描述"}");
                    await StopAsync();
                    break;
                }

                // 处理文本消息
                if (result.MessageType == WebSocketMessageType.Text)
                {
                    var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    OnMessageReceived(message);
                }
                else
                {
                    // 忽略二进制消息（如需支持可扩展）
                    logger.LogWarning("Received an unsupported WebSocket message type: {Type}", result.MessageType);
                    OnMessageReceived($"[警告] 不支持的消息类型: {result.MessageType}");
                }
            }
        }
        catch (WebSocketException ex)
        {
            logger.LogError(ex, "WebSocket receive message failed");
            OnMessageReceived($"[错误] 接收消息失败: {ex.Message}");
            await StopAsync();
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "WebSocket receive message error");
            OnMessageReceived($"[错误] 接收消息异常: {ex.Message}");
        }
    }

    /// <summary>
    ///     清理WebSocket资源
    /// </summary>
    private void CleanupResources()
    {
        _cts?.Cancel();
        _cts?.Dispose();
        _cts = null;

        _webSocket?.Dispose();
        _webSocket = null;
    }

    /// <summary>
    ///     触发消息接收事件（线程安全）
    /// </summary>
    private void OnMessageReceived(string message)
    {
        // 确保在调用线程触发（ViewModel会处理UI线程切换）
        MessageReceived?.Invoke(message);
    }

    /// <summary>
    ///     触发连接状态变更事件
    /// </summary>
    private void OnConnectionStateChanged(bool isConnected)
    {
        ConnectionStateChanged?.Invoke(isConnected);
    }

    #region IDisposable 实现

    public void Dispose()
    {
        Dispose(true);
        GC.SuppressFinalize(this);
    }

    private void Dispose(bool disposing)
    {
        if (_isDisposed) return;

        if (disposing)
        {
            // 手动释放：停止连接并清理资源
            _ = StopAsync();
            CleanupResources();
        }

        _isDisposed = true;
    }

    ~WebsocketService()
    {
        Dispose(false);
    }

    #endregion
}
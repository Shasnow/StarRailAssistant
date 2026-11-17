using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Input;

namespace SRAFrontend.Desktop.Services;

/// <summary>
/// 全局热键录制：持有主窗口，捕获下一次按键。
/// 录制期间在窗口级别监听 KeyUp / PointerPressed，结束后自动退订。
/// </summary>
public sealed class HotkeyCaptureService
{
    private TopLevel? _topLevel;
    private TaskCompletionSource<string?>? _capture;

    public void Attach(TopLevel topLevel) => _topLevel = topLevel;

    /// <summary>
    /// 等待用户按下一个键。返回按键名；按 Esc 或点击其它区域返回 null。
    /// 未绑定窗口或已有录制进行中时立即返回 null。
    /// </summary>
    public Task<string?> CaptureAsync()
    {
        if (_topLevel is null || _capture is not null) return Task.FromResult<string?>(null);

        _capture = new TaskCompletionSource<string?>(TaskCreationOptions.RunContinuationsAsynchronously);
        _topLevel.KeyUp += OnKeyUp;
        _topLevel.PointerPressed += OnPointerPressed;
        return _capture.Task;
    }

    private void OnKeyUp(object? sender, KeyEventArgs e)
    {
        if (_capture is null) return;
        e.Handled = true;
        Finish(e.Key == Key.Escape ? null : e.Key.ToString());
    }

    private void OnPointerPressed(object? sender, PointerPressedEventArgs e) => Finish(null);

    private void Finish(string? key)
    {
        if (_topLevel is not null)
        {
            _topLevel.KeyUp -= OnKeyUp;
            _topLevel.PointerPressed -= OnPointerPressed;
        }

        var capture = _capture;
        _capture = null;
        capture?.TrySetResult(key);
    }
}

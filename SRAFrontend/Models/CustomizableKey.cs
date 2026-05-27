using System;
using Avalonia.Controls;
using Avalonia.Input;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace SRAFrontend.Models;

public partial class CustomizableKey : ObservableObject
{
    [ObservableProperty] private string _currentKey = "";
    [ObservableProperty] private bool _isListening;

    private string _tempKey = "";
    private TopLevel? _topLevel;
    private Action<string>? _setValue;

    public string IconText { get; set; } = "";
    public string DisplayText { get; set; } = "";
    public string DefaultKey { get; init; } = "";

    /// <summary>
    /// 配置绑定参数（不立即绑定，等待 TopLevel 可用）
    /// </summary>
    public CustomizableKey Configure(Func<string> getValue, Action<string> setValue)
    {
        _setValue = setValue;
        CurrentKey = getValue();
        return this;
    }

    /// <summary>
    /// 绑定到 TopLevel 并完成初始化
    /// </summary>
    public void AttachTopLevel(TopLevel topLevel)
    {
        _topLevel = topLevel;
        PropertyChanged += (_, e) =>
        {
            if (e.PropertyName == nameof(CurrentKey) && !IsListening)
                _setValue?.Invoke(CurrentKey);
        };
    }

    [RelayCommand]
    private void ResetToDefault()
    {
        CurrentKey = DefaultKey;
    }

    [RelayCommand]
    private void ModifyKey()
    {
        if (_topLevel is null || IsListening) return;

        _tempKey = CurrentKey;
        IsListening = true;
        CurrentKey = "按键盘设置快捷键";

        _topLevel.KeyUp += OnKeyUp;
        _topLevel.PointerPressed += OnPointerPressed;
    }

    private void StopListening(bool save)
    {
        if (_topLevel is null || !IsListening) return;

        _topLevel.KeyUp -= OnKeyUp;
        _topLevel.PointerPressed -= OnPointerPressed;

        IsListening = false;

        if (save)
            _setValue?.Invoke(CurrentKey);
        else
            CurrentKey = _tempKey;
    }

    private void OnKeyUp(object? sender, KeyEventArgs e)
    {
        if (e.Key == Key.Escape)
        {
            StopListening(false);
            return;
        }
        CurrentKey = e.Key.ToString();
        StopListening(true);
    }

    private void OnPointerPressed(object? sender, PointerPressedEventArgs e)
    {
        StopListening(false);
    }
}

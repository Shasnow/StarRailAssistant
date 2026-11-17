using System;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Desktop.Services;
using SRAFrontend.Localization;

namespace SRAFrontend.Desktop.Models;

public partial class CustomizableKey(HotkeyCaptureService hotkeyCaptureService) : ObservableObject
{
    [ObservableProperty] private string _currentKey = "";
    [ObservableProperty] private bool _isListening;

    private string _tempKey = "";
    private Action<string>? _setValue;

    public string IconText { get; set; } = "";
    public string DisplayText { get; set; } = "";
    public string DefaultKey { get; init; } = "";

    /// <summary>
    /// 配置绑定参数：读取初始键值，并在录制成功后写回。
    /// </summary>
    public CustomizableKey Configure(Func<string> getValue, Action<string> setValue)
    {
        _setValue = setValue;
        CurrentKey = getValue();
        return this;
    }

    [RelayCommand]
    private void ResetToDefault()
    {
        CurrentKey = DefaultKey;
        _setValue?.Invoke(DefaultKey);
    }

    [RelayCommand]
    private async Task ModifyKey()
    {
        if (IsListening) return;

        _tempKey = CurrentKey;
        IsListening = true;
        CurrentKey = Resources.HotkeyCaptureHint;

        var key = await hotkeyCaptureService.CaptureAsync();

        IsListening = false;
        if (key is null)
        {
            CurrentKey = _tempKey;
            return;
        }

        CurrentKey = key;
        _setValue?.Invoke(key);
    }
}

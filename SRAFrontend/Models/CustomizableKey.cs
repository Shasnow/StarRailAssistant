using System;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace SRAFrontend.Models;

public partial class CustomizableKey(Action<CustomizableKey> listenKeyCallback) : ObservableObject
{
    [ObservableProperty] private string _currentKey = "";
    public string IconText { get; set; } = "";
    public string DisplayText { get; set; } = "";
    public string DefaultKey { get; init; } = "";

    public CustomizableKey Bind(Func<string> getValue, Action<string> setValue)
    {
        CurrentKey = getValue();
        PropertyChanged += (_, _) =>
        {
            // 只有一个可观察属性，所以不检查名称也可以
            setValue.Invoke(CurrentKey);
        };
        return this;
    }

    [RelayCommand]
    private void ResetToDefault()
    {
        CurrentKey = DefaultKey;
    }

    [RelayCommand]
    private void ModifyKey()
    {
        listenKeyCallback.Invoke(this);
    }
}
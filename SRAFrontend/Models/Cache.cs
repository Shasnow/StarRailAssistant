using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;

namespace SRAFrontend.Models;

// 继承 ObservableObject 获得属性通知能力
public partial class Cache : ObservableObject
{
    // 自动生成带通知的属性（字段名 _cdkStatus → 属性 CdkStatus）
    [ObservableProperty]
    private string _cdkStatus = "";

    [ObservableProperty]
    private string _cdkStatusForeground = "#F5222D";

    [ObservableProperty]
    private AvaloniaList<string> _configNames = ["Default"];

    [ObservableProperty]
    private string _currentConfigName = "Default";

    // 重点：SelectedConfigIndex 变更时会自动触发通知
    [ObservableProperty]
    private int _selectedConfigIndex = 0;
}
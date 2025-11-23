using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Input;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Views;

public partial class SettingsPageView : UserControl
{
    public SettingsPageView()
    {
        InitializeComponent();
    }

    private string? _capturingProperty; // 当前正在捕获的属性名
    private Button? _capturingButton;   // 当前按钮引用

    protected override void OnLoaded(RoutedEventArgs e)
    {
        if (DataContext is not SettingsPageViewModel viewModel) return;
        var topLevel = TopLevel.GetTopLevel(this);
        viewModel.Zoom = topLevel?.RenderScaling ?? 1;
    }

    private void HotkeyButton_OnClick(object? sender, RoutedEventArgs e)
    {
        if (sender is not Button btn) return;
        if (DataContext is not SettingsPageViewModel vm) return;
        var topLevel = TopLevel.GetTopLevel(this);
        if (topLevel is null) return;

        // 如果已在捕获，再次点击取消
        if (_capturingProperty != null)
        {
            topLevel.KeyDown -= TopLevelOnKeyDown;
            if (_capturingButton != null)
                _capturingButton.IsEnabled = true; // 恢复可用，不修改其内容绑定
            _capturingProperty = null;
            _capturingButton = null;
            return;
        }

        _capturingProperty = btn.Tag?.ToString();
        _capturingButton = btn;
        btn.IsEnabled = false; // 禁用按钮以提示正在捕获，避免破坏绑定
        topLevel.KeyDown += TopLevelOnKeyDown;
    }

    private void TopLevelOnKeyDown(object? sender, KeyEventArgs e)
    {
        if (_capturingProperty == null) return;
        if (DataContext is not SettingsPageViewModel vm) return;
        var prop = vm.Settings.GetType().GetProperty(_capturingProperty);
        if (prop != null)
        {
            // 将按下的键转换为字符串，简单存储 Key 枚举名
            prop.SetValue(vm.Settings, e.Key.ToString());
            // 通过属性 setter 已触发通知，无需手动 OnPropertyChanged（其为受保护成员）
        }
        // 结束捕获
        var topLevel = TopLevel.GetTopLevel(this);
        if (topLevel != null)
            topLevel.KeyDown -= TopLevelOnKeyDown;
        if (_capturingButton != null)
            _capturingButton.IsEnabled = true; // 恢复可用，绑定自动刷新内容
        _capturingProperty = null;
        _capturingButton = null;
    }
}
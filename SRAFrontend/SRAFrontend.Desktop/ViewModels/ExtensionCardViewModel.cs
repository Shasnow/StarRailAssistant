using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Primitives;
using Avalonia.Media;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SRAFrontend.Desktop.Views;
using SukiUI.Controls;
using SukiUI.MessageBox;
using SRAFrontend.Localization;

namespace SRAFrontend.Desktop.ViewModels;

public partial class ExtensionCardViewModel : ObservableObject
{
    private readonly IBackendService _backendService;

    public string Id { get; }
    public string Name { get; }
    public string Description { get; }
    public string ExtensionClass { get; }
    public string ConfigClass { get; }
    /// <summary>扩展目录下 README.md 的原始文本，用于「文档」按钮。</summary>
    public string Readme { get; }

    /// <summary>是否包含执行逻辑：可执行扩展显示运行/停止，其余显示启用/禁用。</summary>
    public bool IsExecutable { get; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    [NotifyPropertyChangedFor(nameof(StatusBrush))]
    [NotifyPropertyChangedFor(nameof(StatusBackground))]
    [NotifyPropertyChangedFor(nameof(ShowRun))]
    [NotifyPropertyChangedFor(nameof(ShowStop))]
    private bool _isRunning;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    [NotifyPropertyChangedFor(nameof(StatusBrush))]
    [NotifyPropertyChangedFor(nameof(StatusBackground))]
    [NotifyPropertyChangedFor(nameof(ShowEnable))]
    [NotifyPropertyChangedFor(nameof(ShowDisable))]
    private bool _isEnabled;

    public bool HasConfig => !string.IsNullOrEmpty(ConfigClass);
    public bool HasReadme => !string.IsNullOrWhiteSpace(Readme);

    public bool ShowRun => IsExecutable && !IsRunning;
    public bool ShowStop => IsExecutable && IsRunning;
    public bool ShowEnable => !IsExecutable && !IsEnabled;
    public bool ShowDisable => !IsExecutable && IsEnabled;

    /// <summary>类名摘要。无配置类时不显示多余的分隔符。</summary>
    public string ClassSummary =>
        HasConfig ? $"{ExtensionClass} / {ConfigClass}" : ExtensionClass;

    /// <summary>状态标签是否处于"活动"状态：可执行扩展看运行状态，其余看启用状态。</summary>
    private bool IsActive => IsExecutable ? IsRunning : IsEnabled;

    /// <summary>状态文案，用于卡片头部的状态标签。</summary>
    public string StatusText => IsExecutable
        ? (IsRunning ? Resources.RunningStatusText : Resources.StoppedStatusText)
        : (IsEnabled ? Resources.EnabledStatusText : Resources.DisabledStatusText);

    /// <summary>状态标签前景色（圆点与文字共用）。</summary>
    public string StatusBrush => IsActive ? "#279F27" : "#8A8A8A";

    /// <summary>状态标签底色，带透明度以避免在深浅色主题下过于刺眼。</summary>
    public string StatusBackground => IsActive ? "#26279F27" : "#22808080";

    public ExtensionCardViewModel(ExtensionInfo info, IBackendService backendService)
    {
        _backendService = backendService;
        Id = info.Id;
        Name = info.Name;
        Description = info.Description;
        ExtensionClass = info.ExtensionClass;
        ConfigClass = info.ConfigClass;
        Readme = info.Readme;
        IsExecutable = info.Executable;
        IsEnabled = info.Enabled ?? false;
    }

    [RelayCommand]
    private async Task RunAsync()
    {
        IsRunning = true;
        await _backendService.SendInputAsync($"extension run {Id}");
    }

    [RelayCommand]
    private async Task StopAsync()
    {
        await _backendService.SendInputAsync($"extension stop {Id}");
        IsRunning = false;
    }

    [RelayCommand]
    private async Task EnableAsync()
    {
        await _backendService.SendInputAsync($"extension enable {Id}");
        IsEnabled = true;
    }

    [RelayCommand]
    private async Task DisableAsync()
    {
        await _backendService.SendInputAsync($"extension disable {Id}");
        IsEnabled = false;
    }

    [RelayCommand]
    private async Task ConfigureAsync()
    {
        var viewModel = new ExtensionConfigDialogViewModel(Id, _backendService);
        var view = new ExtensionConfigDialogView
        {
            DataContext = viewModel
        };
        _ = viewModel.LoadAsync();
        var result = await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = string.Format(Resources.Culture, Resources.ConfigurationTitleFormat, Name),
            Content = view,
            ActionButtonsPreset = SukiMessageBoxButtons.OKCancel
        });
        if (result is SukiMessageBoxResult.OK)
            await viewModel.SaveAsync();
    }

    [RelayCommand]
    private async Task ShowDocAsync()
    {
        if (!HasReadme) return;
        var body = new SelectableTextBlock
        {
            Text = Readme,
            TextWrapping = TextWrapping.Wrap,
            LineHeight = 20
        };
        var content = new ScrollViewer
        {
            Width = 660,
            MaxHeight = 480,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            Content = new Border
            {
                Padding = new Thickness(4, 0, 12, 0),
                Child = body
            }
        };
        await SukiMessageBox.ShowDialog(new SukiMessageBoxHost
        {
            Header = $"{Name} · {Resources.ExtensionDocText}",
            Content = content,
            ActionButtonsPreset = SukiMessageBoxButtons.OK
        });
    }
}

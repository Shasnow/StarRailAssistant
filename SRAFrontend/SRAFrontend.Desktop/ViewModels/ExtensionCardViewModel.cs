using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SRAFrontend.Desktop.Views;
using SukiUI.Controls;
using SukiUI.MessageBox;

namespace SRAFrontend.Desktop.ViewModels;

public partial class ExtensionCardViewModel : ObservableObject
{
    private readonly IBackendService _backendService;

    public string Id { get; }
    public string Name { get; }
    public string Description { get; }
    public string ExtensionClass { get; }
    public string ConfigClass { get; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    [NotifyPropertyChangedFor(nameof(StatusBrush))]
    [NotifyPropertyChangedFor(nameof(StatusBackground))]
    private bool _isRunning;

    public bool HasConfig => !string.IsNullOrEmpty(ConfigClass);

    /// <summary>类名摘要。无配置类时不显示多余的分隔符。</summary>
    public string ClassSummary =>
        HasConfig ? $"{ExtensionClass} / {ConfigClass}" : ExtensionClass;

    /// <summary>运行状态文案，用于卡片头部的状态标签。</summary>
    public string StatusText => IsRunning ? "运行中" : "已停止";

    /// <summary>状态标签前景色（圆点与文字共用）。</summary>
    public string StatusBrush => IsRunning ? "#279F27" : "#8A8A8A";

    /// <summary>状态标签底色，带透明度以避免在深浅色主题下过于刺眼。</summary>
    public string StatusBackground => IsRunning ? "#26279F27" : "#22808080";

    public ExtensionCardViewModel(ExtensionInfo info, IBackendService backendService)
    {
        _backendService = backendService;
        Id = info.Id;
        Name = info.Name;
        Description = info.Description;
        ExtensionClass = info.ExtensionClass;
        ConfigClass = info.ConfigClass;
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
            Header = $"配置 - {Name}",
            Content = view,
            ActionButtonsPreset = SukiMessageBoxButtons.OKCancel
        });
        if (result is SukiMessageBoxResult.OK)
            await viewModel.SaveAsync();
    }
}

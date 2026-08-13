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

    [ObservableProperty] private bool _isRunning;

    public bool HasConfig => !string.IsNullOrEmpty(ConfigClass);

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

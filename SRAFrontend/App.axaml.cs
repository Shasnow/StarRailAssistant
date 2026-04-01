using System.Diagnostics;
using System.Globalization;
using System.Linq;
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Data.Core.Plugins;
using Avalonia.Markup.Xaml;
using Microsoft.Extensions.DependencyInjection;
using Serilog;
using SRAFrontend.Services;
using SRAFrontend.ViewModels;
using SRAFrontend.Views;

namespace SRAFrontend;

public class App : Application
{
    private readonly ServiceProvider? _serviceProvider;

    public App(ServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
    }

    public App() {} // Parameterless constructor for XAML designer

    public override void Initialize() => AvaloniaXamlLoader.Load(this);

    public override void OnFrameworkInitializationCompleted()
    {
        Debug.Assert(_serviceProvider != null, nameof(_serviceProvider) + " != null");
        Localization.Resources.Culture =
            new CultureInfo(
                _serviceProvider.GetRequiredService<SettingsService>().Settings.Language == 0 ? "zh-CN" : "en-US");
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            // Avoid duplicate validations from both Avalonia and the CommunityToolkit. 
            // More info: https://docs.avaloniaui.net/docs/guides/development-guides/data-validation#manage-validationplugins
            DisableAvaloniaDataAnnotationValidation();
            desktop.MainWindow = new MainWindow
            {
                DataContext = _serviceProvider.GetRequiredService<MainWindowViewModel>()
            };
            desktop.Startup += (_, _) =>
            {
                Log.Information("Application is starting up.");
            };
            desktop.Exit += (_, _) =>
            {
                Log.Information("Application is exiting. Saving settings and stopping SRA process.");
                _serviceProvider.GetRequiredService<SettingsService>().SaveSettings();
                _serviceProvider.GetRequiredService<ConfigService>().SaveConfig();
                _serviceProvider.GetRequiredService<CacheService>().SaveCache();
                _serviceProvider.GetRequiredService<IBackendService>().StopBackend();
                _serviceProvider.GetRequiredService<RegistryService>().RestoreUserPcResolution();
                _serviceProvider.GetRequiredService<ReportService>().Report("logout", string.Empty);
                Log.CloseAndFlush();
            };
        }

        base.OnFrameworkInitializationCompleted();
    }

    private void DisableAvaloniaDataAnnotationValidation()
    {
        // Get an array of plugins to remove
        var dataValidationPluginsToRemove =
            BindingPlugins.DataValidators.OfType<DataAnnotationsValidationPlugin>().ToArray();

        // remove each entry found
        foreach (var plugin in dataValidationPluginsToRemove)
        {
            BindingPlugins.DataValidators.Remove(plugin);
        }
    }
}
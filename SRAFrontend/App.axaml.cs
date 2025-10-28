using System.Globalization;
using System.Linq;
using System.Net.Http;
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Data.Core.Plugins;
using Avalonia.Markup.Xaml;
using Microsoft.Extensions.DependencyInjection;
using SRAFrontend.Controls;
using SRAFrontend.Services;
using SRAFrontend.ViewModels;
using SRAFrontend.Views;
using SukiUI.Toasts;

namespace SRAFrontend;

public partial class App : Application
{
    public override void Initialize()
    {
        Localization.Resources.Culture= new CultureInfo("zh-Hans");
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        var serviceCollection = new ServiceCollection();
        ConfigureServices(serviceCollection);
        var serviceProvider = serviceCollection.BuildServiceProvider();
        
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            // Avoid duplicate validations from both Avalonia and the CommunityToolkit. 
            // More info: https://docs.avaloniaui.net/docs/guides/development-guides/data-validation#manage-validationplugins
            DisableAvaloniaDataAnnotationValidation();
            desktop.MainWindow = new MainWindow
            {
                DataContext = serviceProvider.GetRequiredService<MainWindowViewModel>(),
            };
            desktop.Exit += (_, _) =>
            {
                serviceProvider.GetRequiredService<SettingsService>().SaveSettings();
                serviceProvider.GetRequiredService<CacheService>().SaveCache();
                serviceProvider.GetRequiredService<SraService>().StopSraProcess();
                serviceProvider.GetRequiredService<ConfigService>().SaveConfig();
            };
        }

        base.OnFrameworkInitializationCompleted();
    }
    
    private static void ConfigureServices(IServiceCollection services)
    {
        // Register your services here
        services.AddTransient<MainWindowViewModel>(provider =>
        {
            var pages= new PageViewModel[]
            {
                provider.GetRequiredService<HomePageViewModel>(),
                provider.GetRequiredService<TaskPageViewModel>(),
                provider.GetRequiredService<ExtensionPageViewModel>(),
                provider.GetRequiredService<ConsolePageViewModel>(),
                provider.GetRequiredService<SettingsPageViewModel>()
            };
            var toastManager = provider.GetRequiredService<ISukiToastManager>();
            var announcementService = provider.GetRequiredService<AnnouncementService>();
            var settingsService = provider.GetRequiredService<SettingsService>();
            var updateService = provider.GetRequiredService<UpdateService>();
            return new MainWindowViewModel(pages, toastManager, announcementService, settingsService, updateService);
        });
        services.AddTransient<HomePageViewModel>();
        services.AddTransient<TaskPageViewModel>();
        services.AddTransient<ExtensionPageViewModel>();
        services.AddTransient<ConsolePageViewModel>();
        services.AddTransient<SettingsPageViewModel>();
        services.AddSingleton<ControlPanelViewModel>();
        services.AddSingleton<ISukiToastManager, SukiToastManager>();
        services.AddTransient<AnnouncementService>();
        services.AddTransient<HttpClient>();
        services.AddSingleton<SettingsService>();
        services.AddTransient<UpdateService>();
        services.AddSingleton<DataPersistenceService>();
        services.AddSingleton<CacheService>();
        services.AddSingleton<SraService>();
        services.AddSingleton<ConfigService>();
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
using System.Linq;
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Data.Core.Plugins;
using Avalonia.Markup.Xaml;
using Microsoft.Extensions.DependencyInjection;
using SRAFrontend.Controls;
using SRAFrontend.ViewModels;
using SRAFrontend.Views;
using SukiUI.Toasts;

namespace SRAFrontend;

public partial class App : Application
{
    public override void Initialize()
    {
        Localization.Resources.Culture= new System.Globalization.CultureInfo("zh-Hans");
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
                provider.GetRequiredService<LogPageViewModel>(),
                provider.GetRequiredService<SettingPageViewModel>()
            };
            var toastManager = provider.GetRequiredService<ISukiToastManager>();
            return new MainWindowViewModel(pages, toastManager);
        });
        services.AddTransient<HomePageViewModel>();
        services.AddTransient<TaskPageViewModel>();
        services.AddTransient<ExtensionPageViewModel>();
        services.AddTransient<LogPageViewModel>();
        services.AddTransient<SettingPageViewModel>();
        services.AddSingleton<ControlPanelViewModel>();
        services.AddSingleton<ISukiToastManager, SukiToastManager>();
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
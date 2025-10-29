using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net.Http;
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Data.Core.Plugins;
using Avalonia.Markup.Xaml;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Serilog;
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
        InitializeSerilog();
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
                DataContext = serviceProvider.GetRequiredService<MainWindowViewModel>()
            };
            desktop.Startup += (_, _) => Log.Information("Application is starting up.");
            desktop.Exit += (_, _) =>
            {
                Log.Information("Application is exiting. Saving settings and stopping SRA process.");
                serviceProvider.GetRequiredService<SettingsService>().SaveSettings();
                serviceProvider.GetRequiredService<CacheService>().SaveCache();
                serviceProvider.GetRequiredService<SraService>().StopSraProcess();
                serviceProvider.GetRequiredService<ConfigService>().SaveConfig();
                Log.CloseAndFlush();
            };
        }

        base.OnFrameworkInitializationCompleted();
    }
    
    private static void ConfigureServices(IServiceCollection services)
    {
        services.AddLogging(loggingBuilder =>
        {
            loggingBuilder.ClearProviders();
            loggingBuilder.AddSerilog(dispose: true);
        });
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
        services.AddTransient<UpdateService>();
        services.AddTransient<AnnouncementService>();
        services.AddSingleton<ControlPanelViewModel>();
        services.AddSingleton<ISukiToastManager, SukiToastManager>();
        services.AddSingleton<HttpClient>();
        services.AddSingleton<SettingsService>();
        services.AddSingleton<DataPersistenceService>();
        services.AddSingleton<CacheService>();
        services.AddSingleton<SraService>();
        services.AddSingleton<ConfigService>();
    }

    private static void InitializeSerilog()
    {
        // 日志文件路径（存到 ApplicationData/SRA/logs 目录）
        var logDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "SRA",
            "logs"
        );
        Directory.CreateDirectory(logDir); // 确保目录存在

        // 配置 Serilog
        Log.Logger = new LoggerConfiguration()
            // 输出到控制台（开发环境调试用）
            .WriteTo.Console()
            // 输出到文件（按日期拆分，保留 7 天）
            .WriteTo.File(
                path: Path.Combine(logDir, "sra.log"),
                rollingInterval: RollingInterval.Day, // 按天拆分
                retainedFileCountLimit: 7, // 保留 7 天日志
                encoding: System.Text.Encoding.UTF8, // 避免中文乱码
                outputTemplate: "[{Timestamp:yyyy-MM-dd HH:mm:ss} {Level:u3}] {Message:lj}{NewLine}{Exception}"
            )
            // 全局日志级别（生产环境用 Information，开发用 Debug）
            .MinimumLevel.Information()
            // 针对特定命名空间调整日志级别（如服务层用 Debug）
            .MinimumLevel.Override("SRAFrontend.Services", Serilog.Events.LogEventLevel.Debug)
            // 捕获异常时记录堆栈信息
            .Enrich.FromLogContext()
            .CreateLogger();
        AppDomain.CurrentDomain.UnhandledException += (sender, args) =>
        {
            Log.Fatal(args.ExceptionObject as Exception, "应用程序发生未处理的异常，正在终止");
            Log.CloseAndFlush();
        };
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
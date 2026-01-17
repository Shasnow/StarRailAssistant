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
using SRAFrontend.Data;
using SRAFrontend.Services;
using SRAFrontend.ViewModels;
using SRAFrontend.Views;
using SukiUI.Toasts;

namespace SRAFrontend;

public partial class App : Application
{
    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        InitializeSerilog();
        var serviceCollection = new ServiceCollection();
        ConfigureServices(serviceCollection);
        var serviceProvider = serviceCollection.BuildServiceProvider();
        Localization.Resources.Culture =
            new CultureInfo(
                serviceProvider.GetRequiredService<SettingsService>().Settings.Language == 0 ? "zh-CN" : "en-US");
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
                serviceProvider.GetRequiredService<ConfigService>().SaveConfig();
                serviceProvider.GetRequiredService<CacheService>().SaveCache();
                serviceProvider.GetRequiredService<SraService>().StopSraProcess();
                _ = serviceProvider.GetRequiredService<WebsocketService>().StopAsync();
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
        services.AddTransient<MainWindowViewModel>();
        services.AddTransient<PageViewModel, HomePageViewModel>();
        services.AddTransient<PageViewModel, TaskPageViewModel>();
        services.AddTransient<PageViewModel, ExtensionPageViewModel>();
        services.AddTransient<PageViewModel, ConsolePageViewModel>();
        services.AddTransient<PageViewModel, SettingsPageViewModel>();
        services.AddTransient<UpdateService>();
        services.AddTransient<AnnouncementService>();
        services.AddTransient<CommonModel>();
        services.AddSingleton<ControlPanelViewModel>();
        services.AddSingleton<ISukiToastManager, SukiToastManager>();
        services.AddSingleton<SettingsService>();
        services.AddSingleton<CacheService>();
        services.AddSingleton<SraService>();
        services.AddSingleton<WebsocketService>();
        services.AddSingleton<ConfigService>();
        services.AddHttpClient("GlobalClient", client =>
        {
            client.Timeout = TimeSpan.FromSeconds(60);
            client.DefaultRequestHeaders.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0");
        })
        // 优化连接池/DNS
        .ConfigurePrimaryHttpMessageHandler(() => new SocketsHttpHandler
        {
            PooledConnectionLifetime = TimeSpan.FromMinutes(5),
            PooledConnectionIdleTimeout = TimeSpan.FromMinutes(1)
        });
    }

    private static void InitializeSerilog()
    {
        // 日志文件路径（存到 ApplicationData/SRA/logs 目录）
        Directory.CreateDirectory(PathString.FrontendLogsDir); // 确保目录存在

        // 配置 Serilog
        Log.Logger = new LoggerConfiguration()
            // 输出到控制台（开发环境调试用）
            .WriteTo.Console()
            // 输出到文件（按日期拆分，保留 7 天）
            .WriteTo.File(
                path: Path.Combine(PathString.FrontendLogsDir, "sra.log"),
                rollingInterval: RollingInterval.Day, // 按天拆分
                retainedFileCountLimit: 7, // 保留 7 天日志
                encoding: System.Text.Encoding.UTF8, // 避免中文乱码
                outputTemplate: "[{Timestamp:yyyy-MM-dd HH:mm:ss} {Level:u3}] {Message:lj}{NewLine}{Exception}"
            )
            .MinimumLevel.Debug()
            // 捕获异常时记录堆栈信息
            .Enrich.FromLogContext()
            .CreateLogger();
        // 全局未处理异常捕获
        AppDomain.CurrentDomain.UnhandledException += (_, args) =>
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
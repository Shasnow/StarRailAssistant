using System;
using System.CommandLine;
using System.IO;
using System.Net.Http;
using Avalonia;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Serilog;
using SRAFrontend.Controls;
using SRAFrontend.Data;
using SRAFrontend.Localization;
using SRAFrontend.Services;
using SRAFrontend.ViewModels;
using SukiUI.Toasts;

namespace SRAFrontend;

sealed class Program
{
    // Initialization code. Don't use any Avalonia, third-party APIs or any
    // SynchronizationContext-reliant code before AppMain is called: things aren't initialized
    // yet and stuff might break.
    [STAThread]
    public static void Main(string[] args)
    {
        Option<bool> usingPythonOption = new("--using-python");
        Option<string> pythonPathOption = new("--python");
        Option<string> mainPathOption = new("--main");
        RootCommand rootCommand = new("SRAFrontend")
        {
            usingPythonOption,
            pythonPathOption,
            mainPathOption
        };
        var parseResult = rootCommand.Parse(args);
        parseResult.Invoke();
        InitializeSerilog();
        var serviceCollection = new ServiceCollection();
        ConfigureServices(serviceCollection);
        var serviceProvider = serviceCollection.BuildServiceProvider();
        
        var settingsService = serviceProvider.GetRequiredService<SettingsService>();
        // 命令行参数优先级高于设置
        if (parseResult.GetValue(usingPythonOption))
        {
            settingsService.Settings.IsUsingPython = true;
        }

        var pythonPath = parseResult.GetValue(pythonPathOption);
        if (!string.IsNullOrEmpty(pythonPath))
        {
            settingsService.Settings.PythonPath = pythonPath;
        }

        BuildAvaloniaApp(serviceProvider)
                    .StartWithClassicDesktopLifetime(args);
    }

    // Avalonia configuration, don't remove; also used by visual designer.
    private static AppBuilder BuildAvaloniaApp(ServiceProvider serviceProvider)
        => AppBuilder.Configure(() => new App(serviceProvider))
            .UsePlatformDetect()
            .WithInterFont()
            .LogToTrace();
    
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
        // Register backend implementations and proxy
        services.AddSingleton<CliBackendService>();
        services.AddSingleton<PyBackendService>();
        services.AddSingleton<IBackendService, BackendServiceProxy>();
        services.AddSingleton<RegistryService>();
        services.AddSingleton<ConfigService>();
        services.AddSingleton<ReportService>();
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
                outputTemplate: "[{Timestamp:HH:mm:ss} {Level:u3}] {Message:lj}{NewLine}{Exception}"
            )
            .MinimumLevel.Debug()
            // 捕获异常时记录堆栈信息
            .Enrich.FromLogContext()
            .CreateLogger();
        // 全局未处理异常捕获
        AppDomain.CurrentDomain.UnhandledException += (_, args) =>
        {
            Log.Fatal(args.ExceptionObject as Exception, "Unhandled exception occurred");
            Log.CloseAndFlush();
        };
    }
    
}
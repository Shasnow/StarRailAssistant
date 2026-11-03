using System.Runtime.ExceptionServices;
using Avalonia;
using Avalonia.Headless;
using Avalonia.Threading;
using SukiUI;
using Avalonia.Markup.Xaml.Styling;
using Avalonia.Media;
using Avalonia.Styling;
using Xunit;

namespace SRALocalizationChecks;

/// <summary>
/// 无头 Avalonia 宿主：Avalonia 只允许一个 UI 线程，而 xUnit 会把用例分发到不同线程池线程，
/// 因此这里起一个专用线程完成 Setup 并跑 dispatcher 循环，所有 UI 断言都经 <see cref="Run(Action)"/> 调度过去。
/// </summary>
public sealed class AvaloniaSession : IDisposable
{
    private readonly CancellationTokenSource _shutdown = new();
    private readonly TaskCompletionSource _ready = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly Thread _thread;

    public AvaloniaSession()
    {
        _thread = new Thread(RunDispatcher) { IsBackground = true, Name = "Avalonia headless" };
        if (OperatingSystem.IsWindows()) _thread.SetApartmentState(ApartmentState.STA);
        _thread.Start();
        _ready.Task.GetAwaiter().GetResult();
    }

    private void RunDispatcher()
    {
        try
        {
            AppBuilder.Configure<LocalizationApp>()
                .UseSkia()
                .UseHeadless(new AvaloniaHeadlessPlatformOptions { UseHeadlessDrawing = false })
                .SetupWithoutStarting();
            _ready.SetResult();
            Dispatcher.UIThread.MainLoop(_shutdown.Token);
        }
        catch (Exception ex)
        {
            _ready.TrySetException(ex);
        }
    }

    public void Run(Action action)
    {
        try
        {
            Dispatcher.UIThread.Invoke(action);
        }
        catch (AggregateException ex) when (ex.InnerExceptions.Count == 1)
        {
            ExceptionDispatchInfo.Capture(ex.InnerException!).Throw();
        }
    }

    public void Dispose()
    {
        _shutdown.Cancel();
        _thread.Join(TimeSpan.FromSeconds(10));
        _shutdown.Dispose();
    }
}

[CollectionDefinition("Avalonia", DisableParallelization = true)]
public sealed class AvaloniaCollection : ICollectionFixture<AvaloniaSession>
{
}

public sealed class LocalizationApp : Application
{
    public override void Initialize()
    {
        Styles.Add(new StyleInclude(new Uri("avares://SRA/"))
        {
            Source = new Uri("avares://SRA/Styles/Styles.axaml")
        });
        Styles.Add(new SukiTheme { Locale = "zh-CN" });
        Resources["Phosphor"] = new FontFamily("avares://SRA/Assets/Phosphor.ttf#Phosphor");
    }
}

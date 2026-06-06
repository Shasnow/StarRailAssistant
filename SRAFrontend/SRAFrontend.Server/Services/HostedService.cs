using SRAFrontend.Services;

namespace SRAFrontend.Server.Services;

public class HostedService(
    CacheService cacheService,
    SettingsService settingsService,
    ConfigService configService,
    IBackendService backendService) : IHostedService
{
    public Task StartAsync(CancellationToken cancellationToken)
    {
        settingsService.Load();
        cacheService.Load();
        configService.Load();
        return Task.CompletedTask;
    }

    public Task StopAsync(CancellationToken cancellationToken)
    {
        backendService.StopBackend();
        configService.Save();
        settingsService.Save();
        cacheService.SaveCache();
        return Task.CompletedTask;
    }
}

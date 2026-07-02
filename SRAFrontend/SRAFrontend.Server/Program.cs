using Microsoft.AspNetCore.Mvc.Authorization;
using SRAFrontend.Server.Services;
using SRAFrontend.Server.Utils;
using SRAFrontend.Services;

var builder = WebApplication.CreateBuilder(args);

var webUiEnabled = !args.Contains("--no-webui", StringComparer.OrdinalIgnoreCase);

builder.Services.AddSingleton<PyBackendService>();
builder.Services.AddSingleton<CliBackendService>();
builder.Services.AddSingleton<IBackendService, BackendServiceProxy>();
builder.Services.AddSingleton<SettingsService>();
builder.Services.AddSingleton<CacheService>();
builder.Services.AddSingleton<ConfigService>();
builder.Services.AddSingleton<RuntimeTaskService>();
builder.Services.AddSingleton<LogStreamService>();
builder.Services.AddHostedService<HostedService>();
builder.Services.AddHttpClient();

builder.Services.AddAuthentication(TokenAuthenticationOptions.DefaultScheme)
    .AddScheme<TokenAuthenticationOptions, TokenAuthenticationHandler>(
        TokenAuthenticationOptions.DefaultScheme, _ => { });
builder.Services.AddAuthorization();

builder.Services.AddControllers(options =>
{
    options.Filters.Add(new AuthorizeFilter());
});
builder.Services.AddOpenApi();

var app = builder.Build();

if (webUiEnabled)
{
    // The Vue build output is copied into wwwroot by packaging.  ASP.NET Core
    // then serves it as static files while the controllers below provide the
    // actual SRA operations.
    app.UseDefaultFiles();
    app.UseStaticFiles();
}
app.MapOpenApi();

app.UseAuthentication();
app.UseAuthorization();

app.MapGroup("/api").MapControllers();
app.MapGet("/api/health", (IBackendService backendService, RuntimeTaskService runtimeTaskService) =>
{
    var status = runtimeTaskService.GetStatus();
    return Results.Ok(new
    {
        ok = true,
        service = "SRAFrontend.Server",
        webUiEnabled,
        sra = new
        {
            running = status.Running || backendService.IsTaskRunning,
            pid = status.Pid,
            port = 5074,
            detail = status.Detail,
            state = status.State,
            owner = status.Owner,
            mode = status.Mode,
            taskName = status.TaskName,
            configNames = status.ConfigNames,
            startedAt = status.StartedAt,
            lastHeartbeat = status.LastHeartbeat
        }
    });
}).RequireAuthorization();

if (webUiEnabled)
{
    app.MapFallbackToFile("index.html");
}

app.Run();

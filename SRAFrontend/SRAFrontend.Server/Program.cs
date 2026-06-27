using Microsoft.AspNetCore.Mvc.Authorization;
using SRAFrontend.Server.Services;
using SRAFrontend.Server.Utils;
using SRAFrontend.Services;

var builder = WebApplication.CreateBuilder(args);

// SRAFrontend.Server is the single HTTP host for both the API and the optional
// WebUI static files.  Keeping them on one port makes LAN/relay access simple:
// users only need to expose 5074, and token authentication protects the API
// endpoints behind the same origin as the page.
var hasExplicitUrls =
    !string.IsNullOrWhiteSpace(builder.Configuration["urls"]) ||
    !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("ASPNETCORE_URLS"));
if (!hasExplicitUrls)
{
    var webUiPort = builder.Configuration.GetValue("WebUi:Port", 5074);
    var remoteAccess = builder.Configuration.GetValue("WebUi:RemoteAccess", true);
    var webUiHost = remoteAccess
        ? "0.0.0.0"
        : builder.Configuration.GetValue("WebUi:Host", "0.0.0.0");
    builder.WebHost.UseUrls($"http://{webUiHost}:{webUiPort}");
}

var webUiEnabled = builder.Configuration.GetValue("WebUi:Enabled", true);
// --webui / --no-webui only toggles static page hosting.  API endpoints stay
// available because SRA.exe and other tools can use the server without shipping
// or enabling the browser UI bundle.
foreach (var arg in args)
{
    if (arg.Equals("--no-webui", StringComparison.OrdinalIgnoreCase) ||
        arg.Equals("--disable-webui", StringComparison.OrdinalIgnoreCase) ||
        arg.Equals("--webui=false", StringComparison.OrdinalIgnoreCase))
    {
        webUiEnabled = false;
    }
    else if (arg.Equals("--webui", StringComparison.OrdinalIgnoreCase) ||
             arg.Equals("--enable-webui", StringComparison.OrdinalIgnoreCase) ||
             arg.Equals("--webui=true", StringComparison.OrdinalIgnoreCase))
    {
        webUiEnabled = true;
    }
}

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

builder.Services.AddAuthentication(ApiKeyAuthenticationOptions.DefaultScheme)
    .AddScheme<ApiKeyAuthenticationOptions, ApiKeyAuthenticationHandler>(
        ApiKeyAuthenticationOptions.DefaultScheme, _ => { });
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

app.MapControllers();
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

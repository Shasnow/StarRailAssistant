using Microsoft.AspNetCore.Mvc.Authorization;
using ModelContextProtocol.Protocol;
using SRAFrontend.Models;
using SRAFrontend.Server.Controllers;
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
builder.Services.AddSingleton<LogStreamService>();
builder.Services.AddHostedService<HostedService>();
builder.Services.AddHttpClient();
builder.Services.AddMcpServer(options =>
    {
        options.ServerInfo = new Implementation
        {
            Name = "SRA Server",
            Version = AppSettings.Version,
            Description = "StarRailAssistant"
        };
    })
    .WithHttpTransport(option => { option.Stateless = true; })
    .WithTools<McpController>();
var isAuthEnabled = !string.IsNullOrWhiteSpace(builder.Configuration["AccessToken"]);

if (isAuthEnabled)
{
    builder.Services.AddAuthentication(TokenAuthenticationOptions.DefaultScheme)
        .AddScheme<TokenAuthenticationOptions, TokenAuthenticationHandler>(
            TokenAuthenticationOptions.DefaultScheme, _ => { });
    builder.Services.AddAuthorization();
}

builder.Services.AddControllers(options =>
{
    if (isAuthEnabled) options.Filters.Add(new AuthorizeFilter());
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

if (isAuthEnabled)
{
    app.UseAuthentication();
    app.UseAuthorization();
}

if (app.Environment.IsDevelopment())
    app.MapControllers();
else
    app.MapGroup("/api").MapControllers();

app.MapOpenApi();
app.MapMcp("/mcp");
app.Run();
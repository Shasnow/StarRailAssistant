using Microsoft.AspNetCore.Mvc.Authorization;
using ModelContextProtocol.Protocol;
using SRAFrontend.Models;
using SRAFrontend.Server.Controllers;
using SRAFrontend.Server.Services;
using SRAFrontend.Server.Utils;
using SRAFrontend.Services;

var builder = WebApplication.CreateBuilder(args);

const string apiPrefix = "/api";

var webUiEnabled = !args.Contains("--no-webui", StringComparer.OrdinalIgnoreCase);

builder.Services.AddSingleton<PyBackendService>();
builder.Services.AddSingleton<CliBackendService>();
builder.Services.AddSingleton<IBackendService, BackendServiceProxy>();
builder.Services.AddSingleton<SettingsService>();
builder.Services.AddSingleton<CacheService>();
builder.Services.AddSingleton<ConfigService>();
builder.Services.AddSingleton<LogStreamService>();
builder.Services.AddSingleton<AppService>();
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
builder.Services.AddOpenApi(options =>
{
    // MapGroup 的前缀不会反映到 MVC ApiExplorer 生成的 OpenAPI 文档中，这里统一补上
    options.AddDocumentTransformer((document, _, _) =>
    {
        var prefixed = document.Paths.ToDictionary(p => $"{apiPrefix}{p.Key}", p => p.Value);
        document.Paths.Clear();
        foreach (var (path, item) in prefixed)
            document.Paths[path] = item;
        return Task.CompletedTask;
    });
});

var app = builder.Build();

if (webUiEnabled)
{
    app.UseDefaultFiles();
    app.UseStaticFiles();
}

if (isAuthEnabled)
{
    app.UseAuthentication();
    app.UseAuthorization();
}

app.MapGroup(apiPrefix).MapControllers();

app.MapOpenApi();
app.MapMcp("/mcp");
app.Run();
using Microsoft.AspNetCore.Mvc.Authorization;
using SRAFrontend.Server.Services;
using SRAFrontend.Server.Utils;
using SRAFrontend.Services;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddSingleton<PyBackendService>();
builder.Services.AddSingleton<CliBackendService>();
builder.Services.AddSingleton<IBackendService, BackendServiceProxy>();
builder.Services.AddSingleton<SettingsService>();
builder.Services.AddSingleton<CacheService>();
builder.Services.AddSingleton<ConfigService>();
builder.Services.AddSingleton<LogStreamService>();
builder.Services.AddHostedService<HostedService>();

// API Key 认证
var apiKey = builder.Configuration["ApiKey"];
var authEnabled = !string.IsNullOrWhiteSpace(apiKey);
builder.Services.AddAuthentication(ApiKeyAuthenticationOptions.DefaultScheme)
    .AddScheme<ApiKeyAuthenticationOptions, ApiKeyAuthenticationHandler>(
        ApiKeyAuthenticationOptions.DefaultScheme, _ => { });
if (authEnabled)
    builder.Services.AddAuthorization();

builder.Services.AddControllers(options =>
{
    if (authEnabled)
        options.Filters.Add(new AuthorizeFilter());
});
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

var app = builder.Build();

if (!authEnabled)
    app.Logger.LogWarning("ApiKey is not set; server is unsecured.");

// Configure the HTTP request pipeline.
app.MapOpenApi();

// app.UseHttpsRedirection();

if (authEnabled)
{
    app.UseAuthentication();
    app.UseAuthorization();
}

app.MapControllers();

app.Run();
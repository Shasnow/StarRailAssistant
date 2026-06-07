using SRAFrontend.Server.Services;
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
builder.Services.AddControllers();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.UseSwaggerUI(options => { options.SwaggerEndpoint("/openapi/v1.json", "v1"); });
}

// app.UseHttpsRedirection();

app.UseAuthorization();

app.MapControllers();

app.Run();
using System.Security.Claims;
using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Utils;

public class ApiKeyAuthenticationOptions : AuthenticationSchemeOptions
{
    public const string DefaultScheme = "ApiKey";
    public const string HeaderName = "X-Api-Key";
    public const string QueryName = "access_token";
    public const string DefaultToken = "starrailassistant";
}

public class ApiKeyAuthenticationHandler(
    IOptionsMonitor<ApiKeyAuthenticationOptions> options,
    ILoggerFactory logger,
    UrlEncoder encoder,
    IConfiguration configuration,
    SettingsService settingsService)
    : AuthenticationHandler<ApiKeyAuthenticationOptions>(options, logger, encoder)
{
    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var configuredToken = GetConfiguredToken();
        var providedToken = GetProvidedToken();

        if (string.IsNullOrWhiteSpace(providedToken) ||
            !string.Equals(providedToken, configuredToken, StringComparison.Ordinal))
        {
            return Task.FromResult(AuthenticateResult.Fail("Invalid WebUI token"));
        }

        var claims = new[] { new Claim(ClaimTypes.Name, "WebUiUser") };
        var identity = new ClaimsIdentity(claims, Scheme.Name);
        var principal = new ClaimsPrincipal(identity);
        var ticket = new AuthenticationTicket(principal, Scheme.Name);

        return Task.FromResult(AuthenticateResult.Success(ticket));
    }

    private string GetConfiguredToken()
    {
        settingsService.Load();
        var settingsToken = settingsService.Settings.Advanced.WebUiRemoteToken;
        if (!string.IsNullOrWhiteSpace(settingsToken))
            return settingsToken;

        var appSettingsToken = configuration["WebUi:AuthToken"];
        if (!string.IsNullOrWhiteSpace(appSettingsToken))
            return appSettingsToken;

        var legacyApiKey = configuration["ApiKey"];
        return string.IsNullOrWhiteSpace(legacyApiKey)
            ? ApiKeyAuthenticationOptions.DefaultToken
            : legacyApiKey;
    }

    private string? GetProvidedToken()
    {
        if (Request.Headers.TryGetValue(ApiKeyAuthenticationOptions.HeaderName, out var headerValues))
            return headerValues.FirstOrDefault();

        if (Request.Query.TryGetValue(ApiKeyAuthenticationOptions.QueryName, out var queryValues))
            return queryValues.FirstOrDefault();

        return null;
    }
}

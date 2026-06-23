using System.Security.Claims;
using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;

namespace SRAFrontend.Server.Utils;

public class ApiKeyAuthenticationOptions : AuthenticationSchemeOptions
{
    public const string DefaultScheme = "ApiKey";
    public const string HeaderName = "X-Api-Key";
}

public class ApiKeyAuthenticationHandler(
    IOptionsMonitor<ApiKeyAuthenticationOptions> options,
    ILoggerFactory logger,
    UrlEncoder encoder,
    IConfiguration configuration)
    : AuthenticationHandler<ApiKeyAuthenticationOptions>(options, logger, encoder)
{
    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var configuredKey = configuration["ApiKey"];
        if (string.IsNullOrWhiteSpace(configuredKey))
            return Task.FromResult(AuthenticateResult.NoResult());

        if (!Request.Headers.TryGetValue(ApiKeyAuthenticationOptions.HeaderName, out var apiKeyValues))
            return Task.FromResult(AuthenticateResult.Fail("Missing API key"));

        var providedKey = apiKeyValues.FirstOrDefault();
        if (string.IsNullOrWhiteSpace(providedKey) || !string.Equals(providedKey, configuredKey, StringComparison.Ordinal))
            return Task.FromResult(AuthenticateResult.Fail("Invalid API key"));

        var claims = new[] { new Claim(ClaimTypes.Name, "ApiUser") };
        var identity = new ClaimsIdentity(claims, Scheme.Name);
        var principal = new ClaimsPrincipal(identity);
        var ticket = new AuthenticationTicket(principal, Scheme.Name);

        return Task.FromResult(AuthenticateResult.Success(ticket));
    }
}

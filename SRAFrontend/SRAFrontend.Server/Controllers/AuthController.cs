using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Server.Utils;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class AuthController(SettingsService settingsService, IConfiguration configuration) : Controller
{
    [AllowAnonymous]
    [HttpPost("verify")]
    [ProducesResponseType(200)]
    [ProducesResponseType(401)]
    public IActionResult Verify([FromBody] TokenRequest request)
    {
        var token = request.Token?.Trim() ?? "";
        var configuredToken = GetConfiguredToken();
        if (!string.Equals(token, configuredToken, StringComparison.Ordinal))
            return Unauthorized(new { message = "访问令牌不正确" });

        return Ok(new { ok = true });
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
            ? TokenAuthenticationOptions.DefaultToken
            : legacyApiKey;
    }
}

public record TokenRequest(string? Token);

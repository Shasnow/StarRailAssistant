using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class AuthController(IConfiguration configuration) : Controller
{
    [AllowAnonymous]
    [HttpPost]
    [ProducesResponseType(200)]
    [ProducesResponseType(401)]
    public IActionResult Auth([FromBody] TokenRequest request)
    {
        var token = request.Token?.Trim() ?? "";
        var configuredToken = configuration["AccessToken"];
        if (string.IsNullOrWhiteSpace(configuredToken)) return Ok(new R(true, "No access token configured"));
        if (!string.Equals(token, configuredToken, StringComparison.Ordinal))
            return Unauthorized(new R(false, "unauthorized" ));

        return Ok(new R(true, "authorized"));
    }
}

public record TokenRequest(string? Token);

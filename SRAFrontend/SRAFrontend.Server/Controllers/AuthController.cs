using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

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
        if (string.IsNullOrWhiteSpace(configuredToken)) return Ok(new { ok = true });
        if (!string.Equals(token, configuredToken, StringComparison.Ordinal))
            return Unauthorized(new { message = "访问令牌不正确" });

        return Ok(new { ok = true });
    }
}

public record TokenRequest(string? Token);

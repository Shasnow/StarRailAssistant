using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.AspNetCore.Mvc;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.Server.Controllers;

[ApiController]
[Route("[controller]")]
public class ConfigsController(ConfigService configService, CacheService cacheService, IConfiguration configuration) : Controller
{
    [HttpGet]
    [EndpointSummary("获取所有配置名称")]
    [ProducesResponseType(200, Type = typeof(R<List<string>>))]
    public IActionResult GetConfigNames()
    {
        return Ok(new R(true, "success", cacheService.Cache.ConfigNames));
    }

    [HttpGet("{configName}")]
    [EndpointSummary("获取指定配置")]
    [ProducesResponseType(200, Type = typeof(R<TasksConfig>))]
    [ProducesResponseType(404)]
    public IActionResult GetConfig(string configName)
    {
        if (!cacheService.Cache.ConfigNames.Contains(configName))
            return NotFound();

        configService.Load(configName);
        return Ok(new R(true, "success", CreateSafeConfigPayload(configService.TasksConfig)));
    }

    [HttpPost("{configName}")]
    [EndpointSummary("新建配置")]
    [ProducesResponseType(200, Type = typeof(R<string>))]
    [ProducesResponseType(400, Description = "名称包含非法字符")]
    [ProducesResponseType(409, Description = "配置已存在")]
    public IActionResult CreateConfig(string configName)
    {
        if (configName.IndexOfAny(['\\', '/', ':', '*', '?', '"', '<', '>', '|']) != -1)
            return BadRequest("Config name contains invalid characters");

        if (cacheService.Cache.ConfigNames.Contains(configName))
            return Conflict("Config name already exists");

        cacheService.Cache.ConfigNames.Add(configName);
        cacheService.SaveCache();
        return Ok(new R(true, "success", configName));
    }

    [HttpPut("{configName}")]
    [EndpointSummary("更新配置")]
    [ProducesResponseType(200, Type = typeof(R<string>))]
    [ProducesResponseType(404)]
    public IActionResult UpdateConfig(string configName, [FromBody] object body)
    {
        if (!cacheService.Cache.ConfigNames.Contains(configName))
            return NotFound();

        configService.Load(configName);
        var currentStartGame = configService.TasksConfig?.StartGame;
        var jsonElement = JsonSerializer.SerializeToElement(body);
        var config = jsonElement.Deserialize<TasksConfig>();
        if (config is null)
            return BadRequest(new R(false, "Invalid config payload"));

        config.Name = configName;
        if (jsonElement.TryGetProperty("startGame", out var startGame))
        {
            if (startGame.TryGetProperty("username", out var username))
                config.StartGame.Username = username.GetString() ?? "";
            else
                config.StartGame.Username = currentStartGame?.Username ?? "";

            if (startGame.TryGetProperty("password", out var password))
                config.StartGame.Password = password.GetString() ?? "";
            else
                config.StartGame.Password = currentStartGame?.Password ?? "";
        }
        else
        {
            config.StartGame.Username = currentStartGame?.Username ?? "";
            config.StartGame.Password = currentStartGame?.Password ?? "";
        }

        configService.TasksConfig = config;
        configService.Save();
        return Ok(new R(true, "updated"));
    }

    [HttpDelete("{configName}")]
    [EndpointSummary("删除配置")]
    [ProducesResponseType(200, Type = typeof(R<string>))]
    [ProducesResponseType(404)]
    public IActionResult DeleteConfig(string configName)
    {
        if (!cacheService.Cache.ConfigNames.Remove(configName))
            return NotFound();

        return Ok(new R(true, "deleted", configName));
    }

    private object? CreateSafeConfigPayload(TasksConfig? config)
    {
        if (config is null)
            return null;

        var node = JsonSerializer.SerializeToNode(config);
        if (node?["startGame"] is JsonObject startGame)
        {
            // 用 AccessToken 加密敏感字段下发给客户端；未配置 AccessToken 时返回空
            var accessToken = configuration["AccessToken"];
            startGame["username"] = string.IsNullOrEmpty(accessToken)
                ? ""
                : EncryptWithAccessToken(config.StartGame.Username, accessToken);
            startGame["password"] = string.IsNullOrEmpty(accessToken)
                ? ""
                : EncryptWithAccessToken(config.StartGame.Password, accessToken);
        }

        return node;
    }

    /// <summary>
    /// 加密格式：base64(IV[12] + ciphertext + tag[16])，密钥为 AccessToken 的 SHA-256（AES-256-GCM），
    /// 客户端可用 AccessToken 解密还原明文
    /// </summary>
    private static string EncryptWithAccessToken(string plaintext, string accessToken)
    {
        if (string.IsNullOrEmpty(plaintext))
            return string.Empty;

        var key = SHA256.HashData(Encoding.UTF8.GetBytes(accessToken));
        var iv = RandomNumberGenerator.GetBytes(12);
        var plainBytes = Encoding.UTF8.GetBytes(plaintext);
        var cipherBytes = new byte[plainBytes.Length];
        var tag = new byte[16];
        using var aes = new AesGcm(key, 16);
        aes.Encrypt(iv, plainBytes, cipherBytes, tag);

        var payload = new byte[iv.Length + cipherBytes.Length + tag.Length];
        Buffer.BlockCopy(iv, 0, payload, 0, iv.Length);
        Buffer.BlockCopy(cipherBytes, 0, payload, iv.Length, cipherBytes.Length);
        Buffer.BlockCopy(tag, 0, payload, iv.Length + cipherBytes.Length, tag.Length);
        return Convert.ToBase64String(payload);
    }
}

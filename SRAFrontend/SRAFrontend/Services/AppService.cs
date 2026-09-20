using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class AppService(SettingsService settingsService, ILogger<AppService> logger, IHttpClientFactory httpClientFactory)
{
    private static readonly Dictionary<string, string> SpecialBackgroundUrls = new(StringComparer.OrdinalIgnoreCase)
    {
        ["shasnow"] = "https://shasnow.top/gallery/starrailassistant/shasnow.png",
        ["yumemizukimizuki"] = "https://shasnow.top/gallery/starrailassistant/yumemizukimizuki.png"
    };

    private static byte[] DefaultImage { get; } = LoadDefaultImage();

    private static byte[] LoadDefaultImage()
    {
        using var stream = typeof(AppService).Assembly.GetManifestResourceStream("SRAFrontend.Assets.background.default.jpg")
            ?? throw new InvalidOperationException("Embedded default background resource not found");
        using var ms = new MemoryStream();
        stream.CopyTo(ms);
        return ms.ToArray();
    }
    private readonly Dictionary<string, byte[]> _imageCache = new();
    public async Task<byte[]> GetBackgroundImageAsync()
    {
        var backgroundImagePath = settingsService.Settings.Display.BackgroundImageUri;
        var rawUri = backgroundImagePath.Replace("\"", "").Trim();
        if (string.IsNullOrEmpty(rawUri))
            return DefaultImage;

        // 特殊背景：先从缓存读取，不存在则下载并保存到缓存
        if (SpecialBackgroundUrls.ContainsKey(rawUri))
        {
            var cached = await TryLoadSpecialBackgroundAsync(rawUri);
            if (cached != null)
                return cached;
            logger.LogWarning("Failed to load special background {Name}, using default background", rawUri);
            return DefaultImage;
        }

        if (_imageCache.TryGetValue(rawUri, out var image))
            return image;

        try
        {
            byte[] imageBytes;
            if (rawUri.StartsWith("http", StringComparison.OrdinalIgnoreCase))
            {
                using var httpClient = httpClientFactory.CreateClient("GlobalClient");
                using var response = await httpClient.GetAsync(rawUri);

                if (response.IsSuccessStatusCode)
                {
                    imageBytes = await response.Content.ReadAsByteArrayAsync();
                    _imageCache[rawUri] = imageBytes;
                    return imageBytes;
                }
            }
            imageBytes = await File.ReadAllBytesAsync(rawUri);
            _imageCache[rawUri] = imageBytes;
            return imageBytes;
        }
        catch (Exception e)
        {
            logger.LogError("Error loading background: {Message}", e.Message);
        }

        return DefaultImage;
    }
    
    private async Task<byte[]?> TryLoadSpecialBackgroundAsync(string name)
    {   
        var cachePath = Path.Combine(DataPath.BackgroundCacheDir, $"{name}.png");

        // 先尝试从缓存读取
        if (File.Exists(cachePath))
        {
            try
            {
                return await File.ReadAllBytesAsync(cachePath);
            }
            catch (Exception e)
            {
                logger.LogWarning("Cache read failed for {Name}: {Message}", name, e.Message);
            }
        }

        // 缓存不存在或读取失败，从指定链接下载并保存到缓存
        var url = SpecialBackgroundUrls[name];

        try
        {
            using var httpClient = httpClientFactory.CreateClient("GlobalClient");
            using var response = await httpClient.GetAsync(url);
            if (!response.IsSuccessStatusCode)
            {
                logger.LogWarning("Download failed for special background {Name}, status code: {StatusCode}", name, (int)response.StatusCode);
                return null;
            }

            await using var stream = await response.Content.ReadAsStreamAsync();
            await using (var fileStream = new FileStream(cachePath, FileMode.Create, FileAccess.Write))
            {
                await stream.CopyToAsync(fileStream);
            }

            logger.LogInformation("Background {Name} downloaded to {Path}", name, cachePath);
            return await File.ReadAllBytesAsync(cachePath);
        }
        catch (Exception e)
        {
            logger.LogError("Error downloading background {Name}: {Message}", name, e.Message);
            return null;
        }
    }

    public object GetSystemInfo()
    {
        return new
        {
            version = AppSettings.Version,
            osVersion = Environment.OSVersion.ToString(),
            architecture = Environment.Is64BitOperatingSystem ? "x64" : "x86",
            dotnetVersion = Environment.Version.ToString(),
            processorCount = Environment.ProcessorCount,
            cultureInfo = CultureInfo.CurrentCulture.Name,
        };
    }
}
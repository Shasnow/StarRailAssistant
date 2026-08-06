using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using Avalonia.Media.Imaging;
using Avalonia.Platform;
using CommunityToolkit.Mvvm.ComponentModel;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Desktop.Controls;
using SRAFrontend.Services;

namespace SRAFrontend.Desktop.ViewModels;

public partial class HomePageViewModel(
    ControlPanelViewModel controlPanelViewModel,
    SettingsService settingsService,
    ILogger<HomePageViewModel> logger,
    IHttpClientFactory httpClientFactory)
    : PageViewModel(PageName.Home, "\uE2C2")
{
    private static readonly Uri DefaultImagePath = new("avares://SRA/Assets/background/default.jpg");
    private static readonly Bitmap DefaultImage = new(AssetLoader.Open(DefaultImagePath));
    private readonly Dictionary<string, Bitmap> _imageCache = new();

    private static readonly Dictionary<string, string> SpecialBackgroundUrls = new(StringComparer.OrdinalIgnoreCase)
    {
        ["shasnow"] = "https://shasnow.top/gallery/starrailassistant/shasnow.png",
        ["yumemizukimizuki"] = "https://shasnow.top/gallery/starrailassistant/yumemizukimizuki.png"
    };

    [ObservableProperty] private Bitmap? _backgroundImage;
    [ObservableProperty] private bool _isLoadingImage;

    public async Task UpdateBackgroundImageAsync()
    {
        IsLoadingImage = true;
        BackgroundImage = await GetBackgroundImageAsync();
        IsLoadingImage = false;
    }

    private async Task<Bitmap> GetBackgroundImageAsync()
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
            Bitmap bmp;
            if (rawUri.StartsWith("http", StringComparison.OrdinalIgnoreCase))
            {
                using var httpClient = httpClientFactory.CreateClient("GlobalClient");
                using var response = await httpClient.GetAsync(rawUri);

                if (response.IsSuccessStatusCode)
                {
                    await using var stream = await response.Content.ReadAsStreamAsync();
                    bmp = new Bitmap(stream);
                    _imageCache[rawUri] = bmp;
                    return bmp;
                }
            }
            bmp = new Bitmap(rawUri);
            _imageCache[rawUri] = bmp;
            return bmp;
        }
        catch (Exception e)
        {
            logger.LogError("Error loading background: {Message}", e.Message);
        }

        return DefaultImage;
    }

    private async Task<Bitmap?> TryLoadSpecialBackgroundAsync(string name)
    {
        var cachePath = Path.Combine(DataPath.BackgroundCacheDir, $"{name}.png");

        // 先尝试从缓存读取
        if (File.Exists(cachePath))
        {
            try
            {
                return new Bitmap(cachePath);
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
            return new Bitmap(cachePath);
        }
        catch (Exception e)
        {
            logger.LogError("Error downloading background {Name}: {Message}", name, e.Message);
            return null;
        }
    }

    public double ImageOpacity => settingsService.Settings.Display.BackgroundOpacity;
    public double GlassCardOpacity => settingsService.Settings.Display.ControlPanelOpacity;
    public ControlPanelViewModel ControlPanelViewModel => controlPanelViewModel;
}
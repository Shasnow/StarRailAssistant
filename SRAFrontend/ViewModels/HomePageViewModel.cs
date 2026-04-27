using System;
using System.Collections.Generic;
using System.Net.Http;
using Avalonia.Media.Imaging;
using Avalonia.Platform;
using Microsoft.Extensions.Logging;
using SRAFrontend.Controls;
using SRAFrontend.Data;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;

public partial class HomePageViewModel(
    ControlPanelViewModel controlPanelViewModel,
    SettingsService settingsService,
    ILogger<HomePageViewModel> logger,
    IHttpClientFactory httpClientFactory)
    : PageViewModel(PageName.Home, "\uE2C2")
{
    private static readonly Uri DefaultImagePath = new("avares://SRA/Assets/background-lt.jpg");
    private readonly Bitmap _defaultImage = new(AssetLoader.Open(DefaultImagePath));
    private readonly Dictionary<string, Bitmap> _imageCache = new();

    public Bitmap BackgroundImage
    {
        get
        {
            var backgroundImagePath = settingsService.Settings.Display.BackgroundImageUri;

            if (string.IsNullOrEmpty(backgroundImagePath))
                return _defaultImage;

            if (_imageCache.TryGetValue(backgroundImagePath, out var image))
                return image;

            try
            {
                var rawUri = backgroundImagePath.Replace("\"", "").Trim();
                Bitmap bmp;
                if (rawUri.StartsWith("http", StringComparison.OrdinalIgnoreCase))
                {
                    using var httpClient = httpClientFactory.CreateClient("GlobalClient");
                    using var response = httpClient.GetAsync(rawUri).GetAwaiter().GetResult();

                    if (response.IsSuccessStatusCode)
                    {
                        using var stream = response.Content.ReadAsStreamAsync().GetAwaiter().GetResult();
                        bmp = new Bitmap(stream);
                        _imageCache[backgroundImagePath] = bmp;
                        return bmp;
                    }
                }
                bmp = new Bitmap(rawUri);
                _imageCache[backgroundImagePath] = bmp;
                return bmp;
            }
            catch (Exception e)
            {
                logger.LogError("Error loading background: {Message}", e.Message);
            }

            return _defaultImage;
        }
    }

    public double ImageOpacity => settingsService.Settings.Display.BackgroundOpacity;
    public double GlassCardOpacity => settingsService.Settings.Display.ControlPanelOpacity;
    public ControlPanelViewModel ControlPanelViewModel => controlPanelViewModel;
}
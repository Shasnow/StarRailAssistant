using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using Avalonia.Media.Imaging;
using Avalonia.Platform;
using CommunityToolkit.Mvvm.ComponentModel;
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
    private static readonly Bitmap DefaultImage = new(AssetLoader.Open(DefaultImagePath));
    private readonly Dictionary<string, Bitmap> _imageCache = new();
    
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

        if (string.IsNullOrEmpty(backgroundImagePath))
            return DefaultImage;

        if (_imageCache.TryGetValue(backgroundImagePath, out var image))
            return image;

        try
        {
            var rawUri = backgroundImagePath.Replace("\"", "").Trim();
            Bitmap bmp;
            if (rawUri.StartsWith("http", StringComparison.OrdinalIgnoreCase))
            {
                using var httpClient = httpClientFactory.CreateClient("GlobalClient");
                using var response = await httpClient.GetAsync(rawUri);

                if (response.IsSuccessStatusCode)
                {
                    await using var stream = await response.Content.ReadAsStreamAsync();
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

        return DefaultImage;
    }

    public double ImageOpacity => settingsService.Settings.Display.BackgroundOpacity;
    public double GlassCardOpacity => settingsService.Settings.Display.ControlPanelOpacity;
    public ControlPanelViewModel ControlPanelViewModel => controlPanelViewModel;
}
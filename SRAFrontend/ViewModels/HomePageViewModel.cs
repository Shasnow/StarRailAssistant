using System;
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
    ILogger<HomePageViewModel> logger)
    : PageViewModel(PageName.Home, "\uE2C2")
{
    private readonly Uri _defaultImagePath = new("avares://SRA/Assets/background-lt.jpg");

    public Bitmap BackgroundImage
    {
        get
        {
            var backgroundImagePath = settingsService.Settings.BackgroundImagePath;
            Bitmap bitmap;
            try
            {
                bitmap = string.IsNullOrEmpty(backgroundImagePath)
                    ? new Bitmap(AssetLoader.Open(_defaultImagePath))
                    : new Bitmap(backgroundImagePath.Replace("\"", ""));
            }
            catch (Exception e)
            {
                logger.LogError("Failed to load background image from {BackgroundImagePath}: {ErrorMessage}",
                    backgroundImagePath, e.Message);
                bitmap = new Bitmap(AssetLoader.Open(_defaultImagePath));
            }
            return bitmap;
        }
    }

    public double ImageOpacity => settingsService.Settings.BackgroundOpacity;
    public double GlassCardOpacity => settingsService.Settings.CtrlPanelOpacity;
    public ControlPanelViewModel ControlPanelViewModel => controlPanelViewModel;
}
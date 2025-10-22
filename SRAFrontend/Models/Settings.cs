namespace SRAFrontend.Models;

public class Settings
{
    public double BackgroundOpacity { get; set; } = 0.9;
    public int Language { get; set; } = 1; // 0: English, 1: Simplified Chinese
    public double Zoom { get; set; } = 1;
    public string MirrorChyanCdk { get; set; } = "";
}
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace SRAFrontend.utilities;


public static class UrlUtil
{
    /// <summary>
    /// Open the URL in the default browser.
    /// </summary>
    /// <param name="url">The URL to Open</param>
    public static void OpenUrl(string url)
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        else if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
            Process.Start("xdg-open", url);
        else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
            Process.Start("open", url);
    }
}
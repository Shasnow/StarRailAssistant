using SRAFrontend.Controls;

namespace SRAFrontend.Services;

public class OverlayService(IBackendService backendService)
{
    private OverlayWindow? _overlayWindow;

    public void ShowOverlay()
    {
        if (_overlayWindow == null)
        {
            _overlayWindow = new OverlayWindow
            {
                ProcessName = "StarRail"
            };
            backendService.Outputted += BackendServiceOnOutputted;
            _overlayWindow.Closed += (_, _) =>
            {
                backendService.Outputted -= BackendServiceOnOutputted;
                _overlayWindow = null;
            };
        }

        _overlayWindow.Show();
    }

    public void CloseOverlay()
    {
        _overlayWindow?.Close();
    }

    public void SetOverlayDebugInfoEnabled(bool enabled)
    {
        if (_overlayWindow != null) _overlayWindow.IsDebugInfoEnabled = enabled;
    }

    private void BackendServiceOnOutputted(string obj)
    {
        _overlayWindow?.AppendLog(obj);
    }
}
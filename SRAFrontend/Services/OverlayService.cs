using SRAFrontend.Controls;

namespace SRAFrontend.Services;

public class OverlayService(IBackendService backendService)
{
    private OverlayWindow? _overlayWindow;
    
    public void ShowOverlay()
    {
        if (_overlayWindow == null)
        {
            _overlayWindow = new OverlayWindow();
            backendService.Outputted += BackendServiceOnOutputted;
            _overlayWindow.Closed += (_, _) =>
            {
                backendService.Outputted -= BackendServiceOnOutputted;
                _overlayWindow = null;
            };
        }
        _overlayWindow.Show();
    }
    
    public void HideOverlay()
    {
        _overlayWindow?.Hide();
    }

    public void CloseOverlay()
    {
        _overlayWindow?.Close();
    }

    private void BackendServiceOnOutputted(string obj)
    {
        _overlayWindow?.AppendLog(obj);
    }
}
using SRAFrontend.Models;
using SRAFrontend.utilities;

namespace SRAFrontend.Services;

public class SettingsService
{
    private readonly DataPersistenceService _dataPersistenceService;
    public readonly Settings Settings;

    public SettingsService(DataPersistenceService dataPersistenceService)
    {
        _dataPersistenceService = dataPersistenceService;
        Settings = dataPersistenceService.LoadSettings();
        if (Settings.MirrorChyanCdk == "") return;
        Settings.MirrorChyanCdk = EncryptUtil.DecryptString(Settings.MirrorChyanCdk);
    }

    public void SaveSettings()
    {
        if (Settings.MirrorChyanCdk != "") Settings.MirrorChyanCdk = EncryptUtil.EncryptString(Settings.MirrorChyanCdk);
        _dataPersistenceService.SaveSettings(Settings);
    }
}
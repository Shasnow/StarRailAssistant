using System;
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
        if (!string.IsNullOrEmpty(Settings.EncryptedMirrorChyanCdk)) Settings.MirrorChyanCdk = EncryptUtil.DecryptString(Settings.EncryptedMirrorChyanCdk);
    }

    public void SaveSettings()
    {
        Settings.EncryptedMirrorChyanCdk = string.IsNullOrEmpty(Settings.MirrorChyanCdk) ? "" : EncryptUtil.EncryptString(Settings.MirrorChyanCdk);
        _dataPersistenceService.SaveSettings(Settings);
    }
}
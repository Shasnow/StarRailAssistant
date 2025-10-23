using System;
using System.Security.Cryptography;
using System.Text;
using SRAFrontend.Models;

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
        var cdkBytes = Convert.FromBase64String(Settings.MirrorChyanCdk);
        var decodedBytes = ProtectedData.Unprotect(cdkBytes, null, DataProtectionScope.CurrentUser);
        Settings.MirrorChyanCdk = Encoding.UTF8.GetString(decodedBytes);
    }

    public void SaveSettings()
    {
        if (Settings.MirrorChyanCdk != "")
        {
            var cdkBytes = Encoding.UTF8.GetBytes(Settings.MirrorChyanCdk);
            var encodedBytes = ProtectedData.Protect(cdkBytes, null, DataProtectionScope.CurrentUser);
            Settings.MirrorChyanCdk = Convert.ToBase64String(encodedBytes);
        }
        _dataPersistenceService.SaveSettings(Settings);
    }
}
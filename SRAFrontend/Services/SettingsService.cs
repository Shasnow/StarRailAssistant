using System;
using Microsoft.Extensions.Logging;
using SRAFrontend.Models;
using SRAFrontend.Utils;

namespace SRAFrontend.Services;

public class SettingsService
{
    public readonly Settings Settings;
    private readonly ILogger _logger;

    public SettingsService(ILogger<SettingsService> logger)
    {
        _logger = logger;
        _logger.LogInformation("Loading settings...");
        Settings = DataPersister.LoadSettings();
        if (string.IsNullOrEmpty(Settings.EncryptedMirrorChyanCdk))
        {
        }
        else
        {
            string decryptedString;
            try
            {
                decryptedString = EncryptUtil.DecryptString(Settings.EncryptedMirrorChyanCdk);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Failed to decrypt MirrorChyanCdk");
                decryptedString = "";
            }
            Settings.MirrorChyanCdk = decryptedString;
        }

        if (string.IsNullOrEmpty(Settings.EncryptedEmailAuthCode))
        {
        }
        else
        {
            string decryptedAuthCode;
            try
            {
                decryptedAuthCode = EncryptUtil.DecryptString(Settings.EncryptedEmailAuthCode);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Failed to decrypt EmailAuthCode");
                decryptedAuthCode = "";
            }
            Settings.EmailAuthCode = decryptedAuthCode;
        }
    }

    public void SaveSettings()
    {
        string encryptedString;
        if (string.IsNullOrWhiteSpace(Settings.MirrorChyanCdk))
            encryptedString = "";
        else
            try
            {
                encryptedString = EncryptUtil.EncryptString(Settings.MirrorChyanCdk);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Failed to encrypt MirrorChyanCdk");
                encryptedString = "";
            }
        Settings.EncryptedMirrorChyanCdk = encryptedString;

        string encryptedAuthCode;
        if (string.IsNullOrWhiteSpace(Settings.EmailAuthCode))
            encryptedAuthCode = "";
        else
            try
            {
                encryptedAuthCode = EncryptUtil.EncryptString(Settings.EmailAuthCode);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Failed to encrypt EmailAuthCode");
                encryptedAuthCode = "";
            }
        Settings.EncryptedEmailAuthCode = encryptedAuthCode;

        DataPersister.SaveSettings(Settings);
    }
}
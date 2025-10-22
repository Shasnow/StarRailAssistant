using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class SettingsService(DataPersistenceService dataPersistenceService)
{
    public Settings Settings { get; } = dataPersistenceService.LoadSettings();
    public void SaveSettings() => dataPersistenceService.SaveSettings(Settings);
}
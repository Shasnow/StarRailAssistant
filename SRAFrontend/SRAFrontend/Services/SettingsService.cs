using System;
using System.Collections.ObjectModel;
using System.Collections.Specialized;
using System.ComponentModel;
using System.IO;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Migrations;
using SRAFrontend.Models;
using SRAFrontend.Utils;

namespace SRAFrontend.Services;

public class SettingsService(ILogger<SettingsService> logger)
{
    private readonly ILogger _logger = logger;
    private readonly JsonSerializerOptions _jsonSerializerOptions = new() { WriteIndented = true };
    private const int AutoSaveDelayMs = 800;
    
    private CancellationTokenSource? _autoSaveCts;
    public AppSettings Settings { get; private set; } = new ();
    public event PropertyChangedEventHandler? SettingsPropertyChanged;
    public event NotifyCollectionChangedEventHandler? SettingsCollectionChanged;

    public void Load()
    {
        _logger.LogInformation("Loading settings...");
        if (!File.Exists(DataPath.SettingsJson))
        {
            _logger.LogInformation("Settings file not found, using default settings");
            Save();  // 立即创建设置文件
            return;
        }
        var settingsJson = File.ReadAllText(DataPath.SettingsJson);
        try
        {
            if (settingsJson.Contains("EmailAuthCode"))  // 旧格式标志字段
            {
                _logger.LogInformation("Migrating from old settings format...");
                Settings = SettingsMigrator.MigrateOldToNew(JsonSerializer.Deserialize<Settings>(settingsJson, _jsonSerializerOptions)!);
            }
            else
            {
                Settings = JsonSerializer.Deserialize<AppSettings>(settingsJson)!;
            }
            DecryptSensitiveFields();
        }
        catch (Exception)
        {
            _logger.LogError("Failed to load settings, using default settings");
        }
        Subscribe(Settings.General);
        Subscribe(Settings.Notification);
        Subscribe(Settings.Update);
        Subscribe(Settings.Display);
        Subscribe(Settings.Advanced);
        
        // 订阅所有 ObservableCollection 的 CollectionChanged 事件
        SubscribeObservableCollection(Settings.Notification.OnStart);
        SubscribeObservableCollection(Settings.Notification.OnCompleted);
    }

    public void Save()
    {
        _logger.LogInformation("Saving settings...");
        EncryptSensitiveFields();
        var settingsJson = JsonSerializer.Serialize(Settings, _jsonSerializerOptions);
        File.WriteAllText(DataPath.SettingsJson, settingsJson);
    }

    private async Task SaveAsync()
    {
        EncryptSensitiveFields();
        var settingsJson = JsonSerializer.Serialize(Settings, _jsonSerializerOptions);
        await File.WriteAllTextAsync(DataPath.SettingsJson, settingsJson);
    }

    private void EncryptSensitiveFields()
    {
        Settings.Update.EncryptedMirrorChyanCdk = EncryptUtil.EncryptString(Settings.Update.MirrorChyanCdk);
        Settings.Notification.EncryptedSmtpAuthCode = EncryptUtil.EncryptString(Settings.Notification.SmtpAuthCode);
    }

    private void DecryptSensitiveFields()
    {
        Settings.Update.MirrorChyanCdk = EncryptUtil.DecryptString(Settings.Update.EncryptedMirrorChyanCdk);
        Settings.Notification.SmtpAuthCode = EncryptUtil.DecryptString(Settings.Notification.EncryptedSmtpAuthCode);
    }

    private void Subscribe(INotifyPropertyChanged notify)
    {
        notify.PropertyChanged += (sender, args) =>
        {
            SettingsPropertyChanged?.Invoke(sender, args);
            ScheduleAutoSave();
        };
    }
    
    private void SubscribeObservableCollection(ObservableCollection<string> collection)
    {
        collection.CollectionChanged += (sender, args) =>
        {
            SettingsCollectionChanged?.Invoke(sender, args);
            ScheduleAutoSave();
        };
    }
    
    private void ScheduleAutoSave()
    {
        _autoSaveCts?.Cancel();
        _autoSaveCts?.Dispose();
        _autoSaveCts = new CancellationTokenSource();

        _ = Task.Run(async () =>
        {
            try
            {
                await Task.Delay(AutoSaveDelayMs, _autoSaveCts.Token);
                await SaveAsync();
                _logger.LogInformation("Settings auto-saved");
            }
            catch (OperationCanceledException)
            {
                // 连续修改，取消本次，静默忽略
            }
        });
    }

}
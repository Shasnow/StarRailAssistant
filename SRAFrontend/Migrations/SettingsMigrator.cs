using System.Collections.ObjectModel;
using SRAFrontend.Models;

namespace SRAFrontend.Migrations;

public static class SettingsMigrator
{
    public static AppSettings MigrateOldToNew(Settings old)
    {
        var newSettings = new AppSettings
        {
            General = new GeneralSettings
            {
                GamePaths = new ObservableCollection<string>(old.GamePaths),
                GamePathIndex = old.GamePathIndex,
                IsAutoDetectGamePath = old.IsAutoDetectGamePath,
                TemplateMatchConfidence = old.ConfidenceThreshold,
                IsOverlayEnabled = old.IsOverlayEnabled,
                IsGameArgsEnabled = old.LaunchArgumentsEnabled,
                GameArgsWindowSize = old.LaunchArgumentsScreenSize,
                GameArgsFullScreenMode = old.LaunchArgumentsFullScreenMode,
                IsGameArgsPopupWindow = old.LaunchArgumentsPopupWindow,
                GameArgsAdvanced = old.LaunchArgumentsAdvanced,
                IsUseCmd = old.LaunchWithCmd,
                HotkeyStop = old.StartStopHotkey,
                HotkeyF1 = old.ActivityHotkey,
                HotkeyF2 = old.ChronicleHotkey,
                HotkeyF3 = old.WarpHotkey,
                HotkeyF4 = old.GuideHotkey,
                HotkeyE = old.TechniqueHotkey,
                HotkeyM = old.MapHotkey
            },
            Display = new DisplaySettings
            {
                BackgroundImageUri = old.BackgroundImagePath,
                BackgroundOpacity = old.BackgroundOpacity,
                ControlPanelOpacity = old.CtrlPanelOpacity,
                Language = old.Language
            },
            Update = new UpdateSettings
            {
                IsAutoUpdate = old.EnableAutoUpdate,
                DownloadChannel = old.DownloadChannel,
                UpdateChannel = old.AppChannel,
                EncryptedMirrorChyanCdk = old.EncryptedMirrorChyanCdk,
            },
            Advanced = new AdvancedSettings
            {
                BackendLaunchArgs = old.BackendArguments,
                IsDeveloperModeEnabled = old.IsDeveloperMode,
                IsSaveOcrImage = old.IsSaveOcrImage,
                IsUsePython = old.IsUsingPython,
                IsDebugOverlayEnabled = old.IsOverlayDebugInfoEnabled,
                PythonPath = old.PythonPath,
                PythonMain = old.PythonMainPy,
            },
            Notifications = new NotificationSettings
            {
                IsEnabled = old.AllowNotifications,
                IsSystemEnabled = old.AllowSystemNotifications,
                IsEmailEnabled = old.AllowEmailNotifications,
                EncryptedSmtpAuthCode = old.EncryptedEmailAuthCode,
                SmtpServer = old.SmtpServer,
                SmtpPort = old.SmtpPort,
                SmtpReceiver = old.EmailReceiver,
                SmtpSender = old.EmailSender,
                IsWebhookEnabled = old.AllowWebhookNotifications,
                WebhookUrl = old.WebhookEndpoint,
                IsTelegramEnabled = old.AllowTelegramNotifications,
                TelegramBotToken = old.TelegramBotToken,
                TelegramChatId = old.TelegramChatId,
                IsTelegramProxyEnabled = old.TelegramProxyEnabled,
                TelegramProxyUrl = old.TelegramProxyUrl,
                TelegramApiBaseUrl = old.TelegramApiBaseUrl,
                IsTelegramSendImage = old.TelegramSendImage,
                IsServerChanEnabled = old.AllowServerChanNotifications,
                ServerChanSendKey = old.ServerChanSendKey,
                IsOneBotEnabled = old.AllowOneBotNotifications,
                OneBotUrl = old.OneBotEndpoint,
                OneBotGroupId = old.OneBotGroupId,
                OneBotToken = old.OneBotToken,
                OneBotUserId = old.OneBotUserId,
                IsOneBotSendImage = old.OneBotSendImage,
                IsBarkEnabled = old.AllowBarkNotifications,
                BarkDeviceKey = old.BarkDeviceKey,
                BarkServerUrl = old.BarkServerUrl,
                BarkIcon = old.BarkIcon,
                BarkCiphertext = old.BarkCiphertext,
                IsFeishuEnabled = old.AllowFeishuNotifications,
                FeishuWebhookUrl = old.FeishuWebhookUrl,
                FeishuAppId = old.FeishuAppId,
                FeishuAppSecret = old.FeishuAppSecret,
                FeishuReceiveId = old.FeishuReceiveId,
                FeishuReceiveIdType = old.FeishuReceiveIdType,
                IsWeComEnabled = old.AllowWeComNotifications,
                WeComWebhookUrl = old.WeComWebhookUrl,
                IsWeComSendImage = old.WeComSendImage,
                IsDingTalkEnabled = old.AllowDingTalkNotifications,
                DingTalkSecret = old.DingTalkSecret,
                DingTalkWebhookUrl = old.DingTalkWebhookUrl,
                IsDiscordEnabled = old.AllowDiscordNotifications,
                DiscordWebhookUrl = old.DiscordWebhookUrl,
                IsDiscordSendImage = old.DiscordSendImage,
                IsXxtuiEnabled = old.AllowXxtuiNotifications,
                XxtuiChannel = old.XxtuiChannel,
                XxtuiApiKey = old.XxtuiApiKey,
                XxtuiSource = old.XxtuiSource
            }
        };
        return newSettings;
    } 
}
using System;
using System.Threading.Tasks;
using SRAFrontend.Data;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;

public class SettingsPageViewModel : PageViewModel
{
    private readonly CacheService _cacheService;
    private readonly SettingsService _settingsService;
    private readonly UpdateService? _updateService;

    public SettingsPageViewModel() : base(PageName.Setting, "\uE272")
    // Design-time constructor
    {
    }

    public SettingsPageViewModel(
        SettingsService settingsService,
        UpdateService updateService,
        CacheService cacheService) : base(PageName.Setting,
        "\uE272")
    {
        _settingsService = settingsService;
        _updateService = updateService;
        _cacheService = cacheService;
    }

    public string CdkStatus
    {
        get => _cacheService.Cache.CdkStatus;
        set
        {
            _cacheService.Cache.CdkStatus = value;
            OnPropertyChanged();
        }
    }

    public string CdkStatusForeground
    {
        get => _cacheService.Cache.CdkStatusForeground;
        set
        {
            _cacheService.Cache.CdkStatusForeground = value;
            OnPropertyChanged();
        }
    }

    public int CurrentLang
    {
        get => _settingsService.Settings.Language;
        set
        {
            _settingsService.Settings.Language = value;
            OnPropertyChanged();
        }
    }

    public double BackgroundOpacity
    {
        get => _settingsService.Settings.BackgroundOpacity;
        set
        {
            _settingsService.Settings.BackgroundOpacity = value;
            OnPropertyChanged();
        }
    }

    public double Zoom
    {
        get => _settingsService.Settings.Zoom;
        set
        {
            _settingsService.Settings.Zoom = value;
            OnPropertyChanged();
        }
    }

    public string MirrorChyanCdk
    {
        get => _settingsService.Settings.MirrorChyanCdk;
        set
        {
            // 先更新存储的值（即使后续验证失败，也保留用户输入便于修改）
            _settingsService.Settings.MirrorChyanCdk = value;
            OnPropertyChanged(); // 通知UI属性已变更
            if (value == "")
            {
                CdkStatus = "";
                CdkStatusForeground = "#F5222D";
                return;
            }

            // 基础长度校验
            if (value.Length != 24)
            {
                CdkStatus = "CDK长度错误，应为24位字符";
                CdkStatusForeground = "#F5222D";
                return;
            }

            // 长度正确时，触发异步验证（不阻塞setter）
            _ = VerifyCdkAsync(value); // 使用_忽略未等待的Task（需确保异常处理）
        }
    }

    public bool EnableAutoUpdate
    {
        get => _settingsService.Settings.EnableAutoUpdate;
        set
        {
            _settingsService.Settings.EnableAutoUpdate = value;
            OnPropertyChanged();
        }
    }

    public int DownloadChannel
    {
        get => _settingsService.Settings.DownloadChannel;
        set
        {
            _settingsService.Settings.DownloadChannel = value;
            OnPropertyChanged();
        }
    }

    public int AppChannel
    {
        get => _settingsService.Settings.AppChannel;
        set
        {
            _settingsService.Settings.AppChannel = value;
            OnPropertyChanged();
        }
    }

    private async Task VerifyCdkAsync(string cdk)
    {
        // 显示"验证中"状态
        CdkStatus = "验证中...";
        CdkStatusForeground = "#FAAD14"; // 黄色表示处理中

        // 执行异步验证
        var response = await _updateService!.VerifyCdkAsync(cdk);

        if (response is null)
        {
            CdkStatus = "验证失败，无法连接到验证服务";
            CdkStatusForeground = "#F5222D"; // 红色表示错误
            return;
        }

        if (response.Code == 0)
        {
            var leastTime = DateTimeOffset.FromUnixTimeSeconds(response.Data.CdkExpiredTime);
            CdkStatus = "有效的CDK" + $" 到期时间: {leastTime:yyyy-MM-dd HH:mm:ss}";
            CdkStatusForeground = "#279F27"; // 绿色表示成功
        }
        else
        {
            CdkStatus = _updateService.GetErrorMessage(response.Code);
            CdkStatusForeground = "#F5222D"; // 红色表示错误
        }
    }
}
using System;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;

public partial class SettingsPageViewModel(
    SettingsService settingsService,
    UpdateService updateService,
    CacheService cacheService,
    CommonModel commonModel)
    : PageViewModel(PageName.Setting,
        "\uE272")
{
    public Settings Settings => settingsService.Settings;
    public Cache Cache => cacheService.Cache;

    public double Zoom
    {
        get => Settings.Zoom;
        set
        {
            Settings.Zoom = value;
            OnPropertyChanged();
        }
    }

    public string VersionText => Settings.Version.ToString();

    public string MirrorChyanCdk
    {
        get => Settings.MirrorChyanCdk;
        set
        {
            // 先更新存储的值（即使后续验证失败，也保留用户输入便于修改）
            Settings.MirrorChyanCdk = value;
            OnPropertyChanged(); // 通知UI属性已变更
            if (value == "")
            {
                Cache.CdkStatus = "";
                Cache.CdkStatusForeground = "#F5222D";
                return;
            }

            // 基础长度校验
            if (value.Length != 24)
            {
                Cache.CdkStatus = "CDK长度错误，应为24位字符";
                Cache.CdkStatusForeground = "#F5222D";
                return;
            }

            // 长度正确时，触发异步验证（不阻塞setter）
            _ = VerifyCdkAsync(value); // 使用_忽略未等待的Task（需确保异常处理）
        }
    }

    private async Task VerifyCdkAsync(string cdk)
    {
        // 显示"验证中"状态
        Cache.CdkStatus = "验证中...";
        Cache.CdkStatusForeground = "#FAAD14"; // 黄色表示处理中

        // 执行异步验证
        var response = await updateService.VerifyCdkAsync(cdk);

        if (response is null)
        {
            Cache.CdkStatus = "验证失败，无法连接到验证服务";
            Cache.CdkStatusForeground = "#F5222D"; // 红色表示错误
            return;
        }

        if (response.Code == 0)
        {
            var leastTime = DateTimeOffset.FromUnixTimeSeconds(response.Data.CdkExpiredTime);
            Cache.CdkStatus = "有效的CDK" + $" 到期时间: {leastTime:yyyy-MM-dd HH:mm:ss}";
            Cache.CdkStatusForeground = "#279F27"; // 绿色表示成功
        }
        else
        {
            Cache.CdkStatus = updateService.GetErrorMessage(response.Code);
            Cache.CdkStatusForeground = "#F5222D"; // 红色表示错误
        }
    }
    
    [RelayCommand]
    private void CheckForUpdates()
    {
        _ = commonModel.CheckForUpdatesAsync();
    }
    
    [RelayCommand]
    private void CheckAndFixPythonEnvironment()
    {
        _ = commonModel.CheckAndFixPythonEnvironmentAsync();
    }
}
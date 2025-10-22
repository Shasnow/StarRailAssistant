using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class UpdateService(HttpClient httpClient)
{
    private readonly Dictionary<int, string> _errorCodes = new()
    {
        { 1001, "获取版本信息的URL参数不正确" },
        { 7001, "填入的 CDK 已过期" },
        { 7002, "填入的 CDK 错误"},
        { 7003, "填入的 CDK 今日下载次数已达上限" },
        { 7004, "填入的 CDK 类型和待下载的资源不匹配" },
        { 7005, "填入的 CDK 已被封禁" },
        { 8001, "对应架构和系统下的资源不存在" },
        { 8002, "错误的系统参数" },
        { 8003, "错误的架构参数" },
        { 8004, "错误的更新通道参数"}
    };

    private const string BaseVersionUrl =
        "https://mirrorchyan.com/api/resources/StarRailAssistant/latest";
    
    public async Task<VersionResponse?> VerifyCdkAsync(string cdk)
    {
        // Simulate a call to an external service to verify the CDK
        var response = await httpClient.GetAsync($"{BaseVersionUrl}?cdk={cdk}");
        return response.Content.ReadFromJsonAsync<VersionResponse>().Result;
    }
    
    public string GetErrorMessage(int code)
    {
        return _errorCodes.GetValueOrDefault(code, "未知错误");
    }
}
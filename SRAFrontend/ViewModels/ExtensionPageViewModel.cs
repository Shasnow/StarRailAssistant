using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;

public partial class ExtensionPageViewModel : PageViewModel
{
    private readonly IBackendService _backendService;
    private readonly ScriptService _scriptService;

    // ===== 自动对话 =====
    [ObservableProperty] private bool _enableAutoPlot;
    [ObservableProperty] private bool _skipPlot;

    partial void OnEnableAutoPlotChanged(bool value) =>
        _backendService.SendInput(value ? "trigger enable AutoPlotTrigger" : "trigger disable AutoPlotTrigger");

    partial void OnSkipPlotChanged(bool value) =>
        _backendService.SendInput($"trigger set-bool AutoPlotTrigger skip_plot {value}");

    // ===== 脚本仓库 =====
    [ObservableProperty] private AvaloniaList<ScriptRepo> _repos = [];
    [ObservableProperty] private AvaloniaList<RepoScriptInfo> _repoScripts = [];
    [ObservableProperty] private AvaloniaList<ScriptManifest> _installedScripts = [];
    [ObservableProperty] private ScriptRepo? _selectedRepo;
    [ObservableProperty] private RepoScriptInfo? _selectedScript;
    [ObservableProperty] private bool _isLoading;
    [ObservableProperty] private string _statusMessage = "";
    [ObservableProperty] private int _downloadProgress;

    // 添加仓库对话框
    [ObservableProperty] private bool _isAddRepoOpen;
    [ObservableProperty] private string _newRepoName = "";
    [ObservableProperty] private string _newRepoUrl = "";

    public ExtensionPageViewModel(IBackendService backendService, ScriptService scriptService)
        : base(PageName.Extension, "\uE596")
    {
        _backendService = backendService;
        _scriptService = scriptService;
        LoadRepos();
        RefreshInstalled();
    }

    private void LoadRepos()
    {
        Repos.Clear();
        foreach (var r in _scriptService.LoadRepos())
            Repos.Add(r);
    }

    [RelayCommand]
    private void RefreshInstalled()
    {
        InstalledScripts.Clear();
        foreach (var s in _scriptService.GetInstalledScripts())
            InstalledScripts.Add(s);
    }

    [RelayCommand]
    private async Task FetchRepoScripts()
    {
        if (SelectedRepo == null) return;
        IsLoading = true;
        StatusMessage = "正在获取脚本列表...";
        RepoScripts.Clear();
        try
        {
            var scripts = await _scriptService.FetchRepoScriptsAsync(SelectedRepo);
            foreach (var s in scripts)
                RepoScripts.Add(s);
            StatusMessage = $"共 {scripts.Count} 个脚本";
        }
        catch
        {
            StatusMessage = "获取失败，请检查网络或仓库地址";
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    private async Task InstallScript(RepoScriptInfo? info)
    {
        info ??= SelectedScript;
        if (info == null) return;

        IsLoading = true;
        DownloadProgress = 0;

        var progress = new Progress<(int, string)>(p =>
        {
            DownloadProgress = p.Item1;
            StatusMessage = p.Item2;
        });

        var ok = await _scriptService.DownloadAndInstallAsync(info, progress);
        StatusMessage = ok ? $"{info.Name} 安装成功" : $"{info.Name} 安装失败";

        if (ok)
        {
            // 更新本地版本信息
            info.InstalledVersion = info.Version;
            RefreshInstalled();
            await FetchRepoScripts(); // 刷新 hasUpdate 状态
        }
        IsLoading = false;
    }

    [RelayCommand]
    private void UninstallScript(ScriptManifest? script)
    {
        if (script == null) return;
        _scriptService.Uninstall(script.Id);
        StatusMessage = $"{script.Name} 已卸载";
        RefreshInstalled();
    }

    [RelayCommand]
    private async Task CheckUpdates()
    {
        if (SelectedRepo == null) return;
        await FetchRepoScripts();
        var updates = RepoScripts.Count(s => s.HasUpdate);
        StatusMessage = updates > 0 ? $"有 {updates} 个脚本可更新" : "已是最新版本";
    }

    // ===== 仓库管理 =====

    [RelayCommand]
    private void OpenAddRepo()
    {
        NewRepoName = "";
        NewRepoUrl = "";
        IsAddRepoOpen = true;
    }

    [RelayCommand]
    private void CloseAddRepo()
    {
        IsAddRepoOpen = false;
    }

    [RelayCommand]
    private void ConfirmAddRepo()
    {
        if (string.IsNullOrWhiteSpace(NewRepoUrl)) return;
        var name = string.IsNullOrWhiteSpace(NewRepoName) ? NewRepoUrl : NewRepoName;
        _scriptService.AddRepo(name, NewRepoUrl.Trim());
        LoadRepos();
        IsAddRepoOpen = false;
    }

    [RelayCommand]
    private void RemoveRepo(ScriptRepo? repo)
    {
        repo ??= SelectedRepo;
        if (repo == null) return;
        _scriptService.RemoveRepo(repo.Url);
        LoadRepos();
        RepoScripts.Clear();
        SelectedRepo = null;
    }

    partial void OnSelectedRepoChanged(ScriptRepo? value)
    {
        if (value != null)
            _ = FetchRepoScripts();
    }
}

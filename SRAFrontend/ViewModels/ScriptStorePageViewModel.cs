using System;
using System.Linq;
using System.Threading.Tasks;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.ViewModels;

public partial class ScriptStorePageViewModel : PageViewModel
{
    private readonly ScriptService _scriptService;

    // ===== 仓库管理 =====
    [ObservableProperty] private AvaloniaList<ScriptRepo> _repos = [];
    [ObservableProperty] private ScriptRepo? _selectedRepo;
    [ObservableProperty] private bool _isAddRepoOpen;
    [ObservableProperty] private string _newRepoName = "";
    [ObservableProperty] private string _newRepoUrl = "";

    // ===== 脚本列表 =====
    [ObservableProperty] private AvaloniaList<RepoScriptInfo> _repoScripts = [];
    [ObservableProperty] private AvaloniaList<ScriptManifest> _installedScripts = [];
    [ObservableProperty] private RepoScriptInfo? _selectedScript;
    [ObservableProperty] private bool _isLoading;
    [ObservableProperty] private string _statusMessage = "";
    [ObservableProperty] private int _downloadProgress;

    // ===== README =====
    [ObservableProperty] private string _readmeTitle = "";
    [ObservableProperty] private string _readmeContent = "";
    [ObservableProperty] private bool _isReadmeLoading;

    public ScriptStorePageViewModel(ScriptService scriptService)
        : base(PageName.ScriptStore, "\uE396")
    {
        _scriptService = scriptService;
        LoadRepos();
        RefreshInstalled();
    }

    // ===== 仓库管理 =====
    private void LoadRepos()
    {
        Repos.Clear();
        foreach (var r in _scriptService.LoadRepos())
            Repos.Add(r);
        if (Repos.Count > 0 && SelectedRepo == null)
            SelectedRepo = Repos[0];
    }

    [RelayCommand]
    private void OpenAddRepo() => IsAddRepoOpen = true;

    [RelayCommand]
    private void CloseAddRepo()
    {
        IsAddRepoOpen = false;
        NewRepoName = "";
        NewRepoUrl = "";
    }

    [RelayCommand]
    private void ConfirmAddRepo()
    {
        if (string.IsNullOrWhiteSpace(NewRepoUrl)) return;
        // AddRepo 返回 bool，不返回 ScriptRepo 对象
        bool added = _scriptService.AddRepo(NewRepoName, NewRepoUrl);
        if (added) LoadRepos();
        CloseAddRepo();
    }

    [RelayCommand]
    private void RemoveRepo()
    {
        if (SelectedRepo == null) return;
        // RemoveRepo 接收 url 字符串
        _scriptService.RemoveRepo(SelectedRepo.Url);
        Repos.Remove(SelectedRepo);
        SelectedRepo = Repos.FirstOrDefault();
        RepoScripts.Clear();
    }

    partial void OnSelectedRepoChanged(ScriptRepo? value)
    {
        RepoScripts.Clear();
        if (value != null)
            _ = FetchRepoScriptsAsync();
    }

    // ===== 脚本列表 =====
    [RelayCommand]
    private async Task FetchRepoScripts() => await FetchRepoScriptsAsync();

    private async Task FetchRepoScriptsAsync()
    {
        if (SelectedRepo == null || IsLoading) return;
        IsLoading = true;
        StatusMessage = "正在获取脚本列表...";
        try
        {
            var scripts = await _scriptService.FetchRepoScriptsAsync(SelectedRepo);
            RepoScripts.Clear();
            foreach (var s in scripts) RepoScripts.Add(s);
            // 标记已安装状态
            foreach (var rs in RepoScripts)
            {
                var installed = InstalledScripts.FirstOrDefault(i => i.Id == rs.Id);
                rs.InstalledVersion = installed?.Version;
            }
            StatusMessage = $"共 {scripts.Count} 个脚本";
        }
        catch (Exception ex)
        {
            StatusMessage = $"获取失败: {ex.Message}";
        }
        finally { IsLoading = false; }
    }

    [RelayCommand]
    private async Task InstallScript(RepoScriptInfo? info)
    {
        if (info == null || IsLoading) return;
        IsLoading = true;
        StatusMessage = $"正在安装 {info.Name}...";
        try
        {
            // progress 参数类型是 IProgress<(int Percent, string Message)>
            var progress = new Progress<(int Percent, string Message)>(p =>
            {
                DownloadProgress = p.Percent;
                StatusMessage = p.Message;
            });
            var ok = await _scriptService.DownloadAndInstallAsync(info, progress);
            StatusMessage = ok ? $"{info.Name} 安装成功" : $"{info.Name} 安装失败";
            if (ok) RefreshInstalled();
        }
        catch (Exception ex)
        {
            StatusMessage = $"安装失败: {ex.Message}";
        }
        finally { IsLoading = false; DownloadProgress = 0; }
    }

    [RelayCommand]
    private void UninstallScript(ScriptManifest? manifest)
    {
        if (manifest == null) return;
        _scriptService.Uninstall(manifest.Id);
        RefreshInstalled();
        StatusMessage = $"{manifest.Name} 已卸载";
        foreach (var s in RepoScripts)
            if (s.Id == manifest.Id)
                s.InstalledVersion = null;
    }

    [RelayCommand]
    private async Task CheckUpdates()
    {
        if (IsLoading) return;
        IsLoading = true;
        StatusMessage = "检查更新中...";
        try
        {
            int updated = 0;
            foreach (var s in RepoScripts.Where(s => s.HasUpdate).ToList())
            {
                await _scriptService.DownloadAndInstallAsync(s);
                updated++;
            }
            StatusMessage = updated > 0 ? $"已更新 {updated} 个脚本" : "所有脚本已是最新";
            RefreshInstalled();
        }
        finally { IsLoading = false; }
    }

    private void RefreshInstalled()
    {
        InstalledScripts.Clear();
        foreach (var s in _scriptService.GetInstalledScripts())
            InstalledScripts.Add(s);
    }

    // ===== README =====
    [RelayCommand]
    private async Task OpenReadme(RepoScriptInfo? info)
    {
        if (info == null) return;
        ReadmeTitle = info.Name;
        ReadmeContent = "";
        IsReadmeLoading = true;
        ShowReadmeWindow();
        try
        {
            var content = await _scriptService.FetchReadmeAsync(info);
            ReadmeContent = content ?? "_暂无 README_";
        }
        catch { ReadmeContent = "_加载 README 失败_"; }
        finally { IsReadmeLoading = false; }
    }

    [RelayCommand]
    private async Task OpenInstalledReadme(ScriptManifest? manifest)
    {
        if (manifest == null) return;
        ReadmeTitle = manifest.Name;
        IsReadmeLoading = true;
        ReadmeContent = "";
        ShowReadmeWindow();
        await Task.Run(() =>
        {
            ReadmeContent = _scriptService.ReadLocalReadme(manifest.Id) ?? "_暂无 README_";
            IsReadmeLoading = false;
        });
    }

    private void ShowReadmeWindow()
    {
        var win = new SRAFrontend.Views.ReadmeWindow { DataContext = this };
        win.Show();
    }
}

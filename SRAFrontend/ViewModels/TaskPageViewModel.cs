using Avalonia.Collections;
using Avalonia.Controls;
using Avalonia.Data.Converters;
using Avalonia.Platform.Storage;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Extensions.Logging;
using SRAFrontend.Controls;
using SRAFrontend.Data;
using SRAFrontend.Models;
using SRAFrontend.Services;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using System;

namespace SRAFrontend.ViewModels;

/// <summary>已安装 -> 更新/安装 文字转换器</summary>
public class BoolToInstallTextConverter : Avalonia.Data.Converters.IValueConverter
{
    public static readonly BoolToInstallTextConverter Instance = new();
    public object? Convert(object? value, Type targetType, object? parameter,
        System.Globalization.CultureInfo culture)
        => value is true ? "更新" : "安装";
    public object? ConvertBack(object? value, Type targetType, object? parameter,
        System.Globalization.CultureInfo culture) => throw new NotImplementedException();
}

/// <summary>自定义任务的 ClassName 前缀，用于与内置任务区分</summary>
public static class CustomTaskPrefix
{
    public const string Prefix = "CustomTask_";
    public static string Make(string id) => Prefix + id;
    public static bool IsCustom(string className) => className.StartsWith(Prefix);
    public static string GetId(string className) => className.Replace(Prefix, "");
}

/// <summary>任务排序列表项，绑定到拖拽列表</summary>
public partial class TaskOrderItem : ObservableObject
{
    [ObservableProperty] private bool _isEnabled;
    [ObservableProperty] private bool _isSelected;
    public string ClassName { get; set; } = "";
    public string DisplayName { get; set; } = "";
    /// <summary>固定位置，不可移动（启动游戏固定首位，任务完成固定末位）</summary>
    public bool IsFixed { get; set; } = false;
    public bool IsMovable => !IsFixed;
    /// <summary>在 AllTaskDefs 中的原始索引（用于 EnabledTasks 绑定）</summary>
    public int OriginalIndex { get; set; } = -1;
}

/// <summary>
/// 包装 ScriptParamDef + 当前值，供 UI 双向绑定
/// </summary>
public partial class ScriptParamViewModel : ObservableObject
{
    private readonly Action<string, string> _onChanged;
    public ScriptParamDef Def { get; }
    [ObservableProperty]
    private string _value = "";
    public ScriptParamViewModel(ScriptParamDef def, string currentValue, Action<string, string> onChanged)
    {
        Def = def;
        _value = currentValue;
        _onChanged = onChanged;
    }
    partial void OnValueChanged(string value)
    {
        _onChanged(Def.Key, value);
    }
}

public partial class TaskPageViewModel : PageViewModel
{
    private readonly CacheService _cacheService;
    private readonly ConfigService _configService;
    private readonly CommonModel _commonModel;

    [ObservableProperty] private Config _currentConfig;

    [ObservableProperty] private AvaloniaList<TaskOrderItem> _taskOrderList = [];

    [ObservableProperty] [NotifyPropertyChangedFor(nameof(EnableContextMenu))]
    private object? _selectedTaskItem;

    public int CurrencyWarsStrategyIndex
    {
        get => CurrentConfig.CurrencyWarsStrategyIndex;
        set
        {
            CurrentConfig.CurrencyWarsStrategyIndex = value;
            OnPropertyChanged();
            CurrentConfig.CurrencyWarsStrategy = Cache.Strategies.ElementAtOrDefault(value)?.FileName ?? "";
        }
    }

    public TaskPageViewModel(
        CommonModel commonModel,
        ControlPanelViewModel controlPanelViewModel,
        ConfigService configService,
        CacheService cacheService,
        SRAFrontend.Services.ScriptService scriptService,
        ILogger<ScriptConfigEditorViewModel> configEditorLogger) : base(
        PageName.Task, "\uE1BC")
    {
        ControlPanelViewModel = controlPanelViewModel;
        _scriptService = scriptService;
        ScriptConfigEditor = new ScriptConfigEditorViewModel(configEditorLogger);
        _commonModel = commonModel;
        _configService = configService;
        _cacheService = cacheService;
        CurrentConfig = _configService.Config!;

        void OnCachePropertyChanged(object? _, PropertyChangedEventArgs args)
        {
            if (args.PropertyName != nameof(Cache.CurrentConfigIndex)) return;
            _configService.SwitchConfig(_cacheService.Cache.ConfigNames[_cacheService.Cache.CurrentConfigIndex]);
            CurrentConfig = _configService.Config!;
            InitTaskOrderList();
        }

        _cacheService.Cache.PropertyChanged += OnCachePropertyChanged;

        if (Cache.Strategies.Count == 0)
        {
            RefreshStrategies();
        }
        InitTaskOrderList();
    }

    // 固定在首位/末位的任务类名
    private static readonly string FixedFirstTask = "StartGameTask";
    private static readonly string FixedLastTask  = "MissionAccomplishTask";

    // 所有任务的静态定义（类名 -> 显示名）
    private static readonly List<(string ClassName, string DisplayName)> AllTaskDefs =
    [
        ("StartGameTask",         "启动游戏"),
        ("TrailblazePowerTask",   "清开拓力"),
        ("ReceiveRewardsTask",    "领取奖励"),
        ("CosmicStrifeTask",      "旷宇纷争"),
        ("MissionAccomplishTask", "任务完成"),
    ];

    /// <summary>从 Config 初始化任务排序列表</summary>
    private void InitTaskOrderList()
    {
        TaskOrderList.Clear();

        // 构建中间任务的有序列表（排除首尾固定任务）
        var middleDefs = AllTaskDefs.Where(d => d.ClassName != FixedFirstTask && d.ClassName != FixedLastTask).ToList();
        var firstDef = AllTaskDefs.First(d => d.ClassName == FixedFirstTask);
        var lastDef  = AllTaskDefs.First(d => d.ClassName == FixedLastTask);

        List<(string ClassName, string DisplayName, bool Enabled)> middleItems;

        if (CurrentConfig.TaskOrder.Count > 0)
        {
            // 新格式：从 TaskOrder 里提取中间任务的顺序和启用状态
            var orderMap = new Dictionary<string, int>();
            for (int i = 0; i < CurrentConfig.TaskOrder.Count; i++)
                orderMap[CurrentConfig.TaskOrder[i]] = i;

            var enabledMiddle = CurrentConfig.TaskOrder
                .Where(c => c != FixedFirstTask && c != FixedLastTask)
                .Select(c =>
                {
                    // 自定义任务：从 CustomTasks 找 DisplayName
                    if (CustomTaskPrefix.IsCustom(c))
                    {
                        var id = CustomTaskPrefix.GetId(c);
                        var entry = CurrentConfig.CustomTasks.FirstOrDefault(e => e.Id == id);
                        return (c, entry?.Name ?? "自定义任务", true);
                    }
                    return (c, AllTaskDefs.FirstOrDefault(d => d.ClassName == c).DisplayName, true);
                })
                .Where(t => !string.IsNullOrEmpty(t.Item2))
                .ToList();

            var enabledSet = new HashSet<string>(enabledMiddle.Select(t => t.c));
            // 仅对内置任务补充禁用项，自定义任务不需要
            var disabledMiddle = middleDefs
                .Where(d => !enabledSet.Contains(d.ClassName))
                .Select(d => (d.ClassName, d.DisplayName, false))
                .ToList();

            middleItems = enabledMiddle.Concat(disabledMiddle).ToList();
        }
        else
        {
            // 旧格式迁移：EnabledTasks bool 数组
            middleItems = middleDefs.Select((d, i) =>
            {
                int origIdx = AllTaskDefs.FindIndex(x => x.ClassName == d.ClassName);
                bool enabled = origIdx >= 0 && origIdx < CurrentConfig.EnabledTasks.Length && CurrentConfig.EnabledTasks[origIdx];
                return (d.ClassName, d.DisplayName, enabled);
            }).ToList();
        }

        // 首位固定任务（启动游戏）
        bool firstEnabled = CurrentConfig.TaskOrder.Count > 0
            ? CurrentConfig.TaskOrder.Contains(FixedFirstTask)
            : (0 < CurrentConfig.EnabledTasks.Length && CurrentConfig.EnabledTasks[0]);
        TaskOrderList.Add(new TaskOrderItem { ClassName = firstDef.ClassName, DisplayName = firstDef.DisplayName, IsEnabled = firstEnabled, IsFixed = true, OriginalIndex = AllTaskDefs.FindIndex(d => d.ClassName == firstDef.ClassName) });

        // 中间可移动任务
        foreach (var (className, displayName, enabled) in middleItems)
            TaskOrderList.Add(new TaskOrderItem { ClassName = className, DisplayName = displayName, IsEnabled = enabled, IsFixed = false, OriginalIndex = AllTaskDefs.FindIndex(d => d.ClassName == className) });

        // 中间：插入 CustomTasks（按 TaskOrder 里的顺序，或按 CustomTasks 定义顺序）
        foreach (var entry in CurrentConfig.CustomTasks)
        {
            var cClassName = CustomTaskPrefix.Make(entry.Id);
            // 如果 TaskOrder 里没有，说明是新添加的，跳过（AddCustomTask 会处理）
            if (TaskOrderList.Any(t => t.ClassName == cClassName)) continue;
            // 已在上面的 TaskOrder 循环中添加了，此处跳过
        }

        // 末位固定任务（任务完成）
        bool lastEnabled = CurrentConfig.TaskOrder.Count > 0
            ? CurrentConfig.TaskOrder.Contains(FixedLastTask)
            : (4 < CurrentConfig.EnabledTasks.Length && CurrentConfig.EnabledTasks[4]);
        TaskOrderList.Add(new TaskOrderItem { ClassName = lastDef.ClassName, DisplayName = lastDef.DisplayName, IsEnabled = lastEnabled, IsFixed = true, OriginalIndex = AllTaskDefs.FindIndex(d => d.ClassName == lastDef.ClassName) });

        // 监听每个 item 的 IsEnabled 变化，同步回 Config.TaskOrder
        foreach (var item in TaskOrderList)
            item.PropertyChanged += (_, _) => SyncTaskOrderToConfig();

        // 初始化完成后立即同步一次，确保 TaskOrder 包含全部任务顺序
        SyncTaskOrderToConfig();

        // 初始化时通知一次
        OnPropertyChanged(nameof(StartGameTaskEnabled));
        OnPropertyChanged(nameof(TrailblazePowerTaskEnabled));
        OnPropertyChanged(nameof(ReceiveRewardsTaskEnabled));
        OnPropertyChanged(nameof(CosmicStrifeTaskEnabled));
        OnPropertyChanged(nameof(MissionAccomplishTaskEnabled));

        // 默认选中第一个任务
        if (TaskOrderList.Count > 0)
            SelectTask(TaskOrderList[0].ClassName);

        // 监听自定义任务集合变化，保持标签栏同步
        CurrentConfig.CustomTasks.CollectionChanged += (_, _) => SyncCustomTaskLabels();

    }

    /// <summary>根据 ClassName 获取 TaskOrderItem（供各 TaskView 绑定使用）</summary>
    public TaskOrderItem? GetTaskItem(string className)
        => TaskOrderList.FirstOrDefault(t => t.ClassName == className);

    private SRAFrontend.Services.ScriptService _scriptService = null!;

    // 当前选中的任务 ClassName
    private string _selectedClassName = "StartGameTask";

    /// <summary>已安装脚本列表（供自定义任务选择）</summary>
    public System.Collections.ObjectModel.ObservableCollection<SRAFrontend.Models.ScriptManifest> InstalledScripts { get; }
        = new();

    public AvaloniaList<ScriptParamViewModel> ScriptParams { get; } = new();

    public bool HasScriptParams => ScriptParams.Count > 0;

    public ScriptConfigEditorViewModel ScriptConfigEditor { get; }

    /// <summary>当前选中的自定义任务条目（仅当选中的是自定义任务时有值）</summary>
    public SRAFrontend.Models.CustomTaskEntry? SelectedCustomTask
        => CustomTaskPrefix.IsCustom(_selectedClassName)
            ? CurrentConfig.CustomTasks.FirstOrDefault(t =>
                CustomTaskPrefix.Make(t.Id) == _selectedClassName)
            : null;

    // ===== 已安装脚本选择 =====

    private SRAFrontend.Models.ScriptManifest? _selectedInstalledScript;
    public SRAFrontend.Models.ScriptManifest? SelectedInstalledScript
    {
        get => _selectedInstalledScript;
        set
        {
            _selectedInstalledScript = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(SelectedScriptTasks));
            OnPropertyChanged(nameof(SelectedScriptHasMultipleTasks));
            // 自动选中第一个任务
            SelectedScriptTask = value?.Tasks.FirstOrDefault();
            // 如果只有一个任务，直接应用
            if (value != null && value.Tasks.Count == 1)
                ApplyScriptSelection(value, value.Tasks[0]);
        }
    }

    public System.Collections.Generic.List<SRAFrontend.Models.ScriptTaskDef> SelectedScriptTasks
        => _selectedInstalledScript?.Tasks ?? [];

    public bool SelectedScriptHasMultipleTasks
        => (_selectedInstalledScript?.Tasks.Count ?? 0) > 1;

    private SRAFrontend.Models.ScriptTaskDef? _selectedScriptTask;
    public SRAFrontend.Models.ScriptTaskDef? SelectedScriptTask
    {
        get => _selectedScriptTask;
        set
        {
            _selectedScriptTask = value;
            OnPropertyChanged();
            if (_selectedInstalledScript != null && value != null)
                ApplyScriptSelection(_selectedInstalledScript, value);
        }
    }

    /// <summary>把选中的脚本+任务写入当前 CustomTaskEntry</summary>
    private void ApplyScriptSelection(SRAFrontend.Models.ScriptManifest script,
        SRAFrontend.Models.ScriptTaskDef task)
    {
        if (SelectedCustomTask == null) return;
        SelectedCustomTask.ScriptId = script.Id;
        SelectedCustomTask.TaskEntry = task.Entry;
        SelectedCustomTask.TaskClassName = task.Class;
        // 如果任务名还是默认值，自动填任务名
        if (SelectedCustomTask.Name.StartsWith("自定义任务"))
            SelectedCustomTask.Name = task.Name;
        // 同步标签栏显示名
        var item = TaskOrderList.FirstOrDefault(t =>
            t.ClassName == CustomTaskPrefix.Make(SelectedCustomTask.Id));
        if (item != null) item.DisplayName = SelectedCustomTask.Name;
        // 清空手动路径（避免混用）
        SelectedCustomTask.ScriptPath = "";
        OnPropertyChanged(nameof(SelectedCustomTask));
        SyncTaskOrderToConfig();

        // 加载参数定义（BGI 风格 settings.json 优先）
        ScriptParams.Clear();
        OnPropertyChanged(nameof(HasScriptParams));
        var paramDefs = script.LoadedParams.Count > 0 ? script.LoadedParams : task.Params;
        foreach (var p in paramDefs)
        {
            if (SelectedCustomTask.Params == null)
                SelectedCustomTask.Params = new System.Collections.Generic.Dictionary<string, string>();
            if (!SelectedCustomTask.Params.ContainsKey(p.Key))
                SelectedCustomTask.Params[p.Key] = p.Default ?? "";
            var vm = new ScriptParamViewModel(p, SelectedCustomTask.Params.GetValueOrDefault(p.Key, ""),
                (key, val) => {
                    if (SelectedCustomTask.Params == null)
                        SelectedCustomTask.Params = new System.Collections.Generic.Dictionary<string, string>();
                    SelectedCustomTask.Params[key] = val;
                    _configService.SaveConfig();
                });
            ScriptParams.Add(vm);
        }

        OnPropertyChanged(nameof(HasScriptParams));
        // 加载脚本的 config.json 编辑器
        ScriptConfigEditor.Load(script.Id);
    }

    /// <summary>设置当前任务的参数值</summary>
    public void SetParam(string key, string value)
    {
        if (SelectedCustomTask == null) return;
        if (SelectedCustomTask.Params == null)
            SelectedCustomTask.Params = new System.Collections.Generic.Dictionary<string, string>();
        SelectedCustomTask.Params[key] = value;
        _configService.SaveConfig();
    }

    /// <summary>获取当前任务的参数值（供 UI 绑定用）</summary>
    public string GetParam(string key)
    {
        if (SelectedCustomTask?.Params?.TryGetValue(key, out var v) == true)
            return v ?? "";
        // 返回 manifest 中定义的默认值
        var def = ScriptParams.FirstOrDefault(p => p.Def.Key == key);
        return def?.Def.Default ?? "";
    }

    [RelayCommand]
    private void OpenScriptConfig()
    {
        if (SelectedCustomTask == null || string.IsNullOrEmpty(SelectedCustomTask.ScriptId)) return;

        var scriptId = SelectedCustomTask.ScriptId;
        var appData = System.Environment.GetFolderPath(System.Environment.SpecialFolder.ApplicationData);
        var configDir = System.IO.Path.Combine(appData, "SRA", "scripts", scriptId);

        // 收集参数定义：settings.json 优先，其次 manifest params
        var paramDefs = new System.Collections.Generic.List<SRAFrontend.Models.ScriptParamDef>();

        // 检查 settings.json 是否存在
        var settingsPath = System.IO.Path.Combine(configDir, "settings.json");
        bool hasSettingsFile = System.IO.File.Exists(settingsPath);

        var manifest = InstalledScripts.FirstOrDefault(s => s.Id == scriptId);
        if (manifest != null)
        {
            if (manifest.LoadedParams.Count > 0)
                paramDefs.AddRange(manifest.LoadedParams);
            else if (!hasSettingsFile)
                foreach (var task in manifest.Tasks)
                    paramDefs.AddRange(task.Params);
        }

        var vm = new ScriptConfigWindowViewModel(scriptId, configDir, paramDefs);
        var win = new SRAFrontend.Views.ScriptConfigWindow { DataContext = vm };
        win.Show();
    }

    [RelayCommand]
    public void RefreshInstalledScripts()
    {
        var prev = _selectedInstalledScript?.Id;
        InstalledScripts.Clear();
        foreach (var s in _scriptService.GetInstalledScripts())
            InstalledScripts.Add(s);
        // 恢复之前的选中状态（如果当前有自定义任务已选了某个脚本）
        if (SelectedCustomTask != null && !string.IsNullOrEmpty(SelectedCustomTask.ScriptId))
        {
            _selectedInstalledScript = InstalledScripts
                .FirstOrDefault(s => s.Id == SelectedCustomTask.ScriptId);
            OnPropertyChanged(nameof(SelectedInstalledScript));
            OnPropertyChanged(nameof(SelectedScriptTasks));
            OnPropertyChanged(nameof(SelectedScriptHasMultipleTasks));
            if (_selectedInstalledScript != null)
                _selectedScriptTask = _selectedInstalledScript.Tasks
                    .FirstOrDefault(t => t.Entry == SelectedCustomTask.TaskEntry);
            OnPropertyChanged(nameof(SelectedScriptTask));
        }
    }

    /// <summary>选中指定任务，更新 IsSelected 状态</summary>
    public void SelectTask(string className)
    {
        _selectedClassName = className;
        foreach (var item in TaskOrderList)
            item.IsSelected = item.ClassName == className;
        OnPropertyChanged(nameof(StartGameTaskSelected));
        OnPropertyChanged(nameof(TrailblazePowerTaskSelected));
        OnPropertyChanged(nameof(ReceiveRewardsTaskSelected));
        OnPropertyChanged(nameof(CosmicStrifeTaskSelected));
        OnPropertyChanged(nameof(MissionAccomplishTaskSelected));
        OnPropertyChanged(nameof(CustomTaskSelected));
        OnPropertyChanged(nameof(SelectedCustomTask));

        // 切换到自定义任务时，恢复该任务对应的脚本选择状态
        if (CustomTaskPrefix.IsCustom(className))
            RefreshInstalledScripts();
    }

    public bool CustomTaskSelected => CustomTaskPrefix.IsCustom(_selectedClassName);

    // 各任务内容区域的显示控制
    public bool StartGameTaskSelected         => _selectedClassName == "StartGameTask";
    public bool TrailblazePowerTaskSelected   => _selectedClassName == "TrailblazePowerTask";
    public bool ReceiveRewardsTaskSelected    => _selectedClassName == "ReceiveRewardsTask";
    public bool CosmicStrifeTaskSelected      => _selectedClassName == "CosmicStrifeTask";
    public bool MissionAccomplishTaskSelected => _selectedClassName == "MissionAccomplishTask";

    // 各任务启用状态属性（供 TaskView 绑定，替代 EnabledTasks[n]）
    public bool StartGameTaskEnabled
    {
        get => GetTaskItem("StartGameTask")?.IsEnabled ?? false;
        set { var t = GetTaskItem("StartGameTask"); if (t != null) t.IsEnabled = value; }
    }
    public bool TrailblazePowerTaskEnabled
    {
        get => GetTaskItem("TrailblazePowerTask")?.IsEnabled ?? false;
        set { var t = GetTaskItem("TrailblazePowerTask"); if (t != null) t.IsEnabled = value; }
    }
    public bool ReceiveRewardsTaskEnabled
    {
        get => GetTaskItem("ReceiveRewardsTask")?.IsEnabled ?? false;
        set { var t = GetTaskItem("ReceiveRewardsTask"); if (t != null) t.IsEnabled = value; }
    }
    public bool CosmicStrifeTaskEnabled
    {
        get => GetTaskItem("CosmicStrifeTask")?.IsEnabled ?? false;
        set { var t = GetTaskItem("CosmicStrifeTask"); if (t != null) t.IsEnabled = value; }
    }
    public bool MissionAccomplishTaskEnabled
    {
        get => GetTaskItem("MissionAccomplishTask")?.IsEnabled ?? false;
        set { var t = GetTaskItem("MissionAccomplishTask"); if (t != null) t.IsEnabled = value; }
    }

    /// <summary>把当前列表状态同步回 Config.TaskOrder</summary>
    private void SyncTaskOrderToConfig()
    {
        // TaskOrder 保存所有任务的顺序（不过滤启用状态）
        // EnabledTasks 继续负责启用状态，由各 TaskView 的 CheckBox 直接绑定
        CurrentConfig.TaskOrder.Clear();
        foreach (var item in TaskOrderList)
            CurrentConfig.TaskOrder.Add(item.ClassName);
        // 通知各任务 IsEnabled 属性变化
        OnPropertyChanged(nameof(StartGameTaskEnabled));
        OnPropertyChanged(nameof(TrailblazePowerTaskEnabled));
        OnPropertyChanged(nameof(ReceiveRewardsTaskEnabled));
        OnPropertyChanged(nameof(CosmicStrifeTaskEnabled));
        OnPropertyChanged(nameof(MissionAccomplishTaskEnabled));
    }

    [RelayCommand]
    private void MoveTaskUp(TaskOrderItem item)
    {
        if (item.IsFixed) return;
        var idx = TaskOrderList.IndexOf(item);
        if (idx <= 0) return;
        // 不能移到固定首位任务之前
        var prev = TaskOrderList[idx - 1];
        if (prev.IsFixed) return;
        TaskOrderList.RemoveAt(idx);
        TaskOrderList.Insert(idx - 1, item);
        item.PropertyChanged += (_, _) => SyncTaskOrderToConfig();
        SyncTaskOrderToConfig();
    }

    [RelayCommand]
    private void MoveTaskDown(TaskOrderItem item)
    {
        if (item.IsFixed) return;
        var idx = TaskOrderList.IndexOf(item);
        if (idx < 0 || idx >= TaskOrderList.Count - 1) return;
        // 不能移到固定末位任务之后
        var next = TaskOrderList[idx + 1];
        if (next.IsFixed) return;
        TaskOrderList.RemoveAt(idx);
        TaskOrderList.Insert(idx + 1, item);
        item.PropertyChanged += (_, _) => SyncTaskOrderToConfig();
        SyncTaskOrderToConfig();
    }

    [RelayCommand]
    private void AddCustomTask()
    {
        RefreshInstalledScripts();
        var entry = new SRAFrontend.Models.CustomTaskEntry
        {
            Name = $"自定义任务 {CurrentConfig.CustomTasks.Count + 1}",
            ScriptId = "",
            TaskEntry = "",
            TaskClassName = "",
            ScriptPath = "",
            IsEnabled = true
        };
        CurrentConfig.CustomTasks.Add(entry);

        // 插入到末位固定任务之前
        var className = CustomTaskPrefix.Make(entry.Id);
        var lastFixed = TaskOrderList.LastOrDefault(t => t.IsFixed);
        var insertIdx = lastFixed != null ? TaskOrderList.IndexOf(lastFixed) : TaskOrderList.Count;
        var newItem = new TaskOrderItem
        {
            ClassName = className,
            DisplayName = entry.Name,
            IsEnabled = true,
            IsFixed = false,
            OriginalIndex = -1
        };
        newItem.PropertyChanged += (_, _) => SyncTaskOrderToConfig();
        TaskOrderList.Insert(insertIdx, newItem);
        SyncTaskOrderToConfig();
        SelectTask(className);
    }

    [RelayCommand]
    private void RemoveCustomTask()
    {
        if (SelectedCustomTask == null) return;
        var className = CustomTaskPrefix.Make(SelectedCustomTask.Id);
        var item = TaskOrderList.FirstOrDefault(t => t.ClassName == className);
        if (item != null) TaskOrderList.Remove(item);
        CurrentConfig.CustomTasks.Remove(SelectedCustomTask);
        SyncTaskOrderToConfig();
        // 选中第一个任务
        if (TaskOrderList.Count > 0) SelectTask(TaskOrderList[0].ClassName);
    }

    [RelayCommand]
    private async System.Threading.Tasks.Task SelectCustomTaskScript()
    {
        if (SelectedCustomTask == null || TopLevelObject == null) return;
        var files = await TopLevelObject.StorageProvider.OpenFilePickerAsync(new Avalonia.Platform.Storage.FilePickerOpenOptions
        {
            Title = "选择 Python 脚本文件",
            AllowMultiple = false,
            FileTypeFilter = [new Avalonia.Platform.Storage.FilePickerFileType("Python 脚本") { Patterns = ["*.py"] }]
        });
        if (files.Count == 0) return;
        SelectedCustomTask.ScriptPath = files[0].Path.LocalPath;
        // 同步标签名（如果名称还是默认值）
        var item = TaskOrderList.FirstOrDefault(t => t.ClassName == CustomTaskPrefix.Make(SelectedCustomTask.Id));
        if (item != null) OnPropertyChanged(nameof(SelectedCustomTask));
    }

    [RelayCommand]
    private void SingleCustomTask()
    {
        if (SelectedCustomTask == null) return;
        var className = CustomTaskPrefix.Make(SelectedCustomTask.Id);
        SingleTask(CustomTaskPrefix.Make(SelectedCustomTask.Id));
    }

    private void SyncCustomTaskLabels()
    {
        foreach (var entry in CurrentConfig.CustomTasks)
        {
            var className = CustomTaskPrefix.Make(entry.Id);
            var item = TaskOrderList.FirstOrDefault(t => t.ClassName == className);
            if (item != null) item.DisplayName = entry.Name;
        }
    }

    /// <summary>拖拽时直接移动到指定索引位置</summary>
    public void MoveTaskToIndex(TaskOrderItem item, int targetIndex)
    {
        if (item.IsFixed) return;
        var idx = TaskOrderList.IndexOf(item);
        if (idx < 0 || idx == targetIndex) return;
        if (targetIndex < 0 || targetIndex >= TaskOrderList.Count) return;
        // 不能越过固定任务的边界
        var target = TaskOrderList[targetIndex];
        if (target.IsFixed) return;
        TaskOrderList.RemoveAt(idx);
        TaskOrderList.Insert(targetIndex, item);
        item.PropertyChanged += (_, _) => SyncTaskOrderToConfig();
        SyncTaskOrderToConfig();
    }

    public ControlPanelViewModel ControlPanelViewModel { get; }

    public AvaloniaList<TrailblazePowerTask> Tasks => [
            new(AddTaskItem)
            {
                Title = "饰品提取",
                Id = "ornament_extraction",
                Cost = 40,
                Levels = new[]
                {
                    "---选择副本---",
                    "鎏金追忆（朋克洛德/千星城）",
                    "西风丛中（翁法罗斯/天国@直播间）",
                    "月下朱殷（妖精/海隅）",
                    "纷争不休（拾骨地/巨树）",
                    "蠹役饥肠（露莎卡/蕉乐园）",
                    "永恒笑剧（都蓝/劫火）",
                    "伴你入眠（茨冈尼亚/出云显世）",
                    "天剑如雨（格拉默/匹诺康尼）",
                    "孽果盘生（繁星/龙骨）",
                    "百年冻土（贝洛伯格/萨尔索图）",
                    "温柔话语（公司/差分机）",
                    "浴火钢心（塔利亚/翁瓦克）",
                    "坚城不倒（太空封印站/仙舟）"
                },
                MaxSingleTimes = 6
            },

            new(AddTaskItem)
            {
                Title = "拟造花萼（金）",
                Id = "calyx_golden",
                Cost = 10,
                Levels = new[]
                {
                    "---选择副本---",
                    "回忆之蕾（二相乐园）",
                    "以太之蕾（二相乐园）",
                    "珍藏之蕾（二相乐园）",
                    "回忆之蕾（翁法罗斯）",
                    "以太之蕾（翁法罗斯）",
                    "珍藏之蕾（翁法罗斯）",
                    "回忆之蕾（匹诺康尼）",
                    "以太之蕾（匹诺康尼）",
                    "珍藏之蕾（匹诺康尼）",
                    "回忆之蕾（仙舟罗浮）",
                    "以太之蕾（仙舟罗浮）",
                    "珍藏之蕾（仙舟罗浮）",
                    "回忆之蕾（雅利洛VI）",
                    "以太之蕾（雅利洛VI）",
                    "珍藏之蕾（雅利洛VI）"
                },
                MaxSingleTimes = 24
            },

            new(AddTaskItem)
            {
                Title = "拟造花萼（赤）",
                Id = "calyx_crimson",
                Cost = 10,
                Levels = new[]
                {
                    "---选择副本---",
                    "月狂獠牙（毁灭）",
                    "净世残刃（毀灭）",
                    "神体琥珀（存护）",
                    "琥珀的坚守（存护）",
                    "天谴血矛（巡猎）",
                    "逆时一击（巡猎）",
                    "逐星之矢（巡猎）",
                    "万象果实（丰饶）",
                    "永恒之花（丰饶）",
                    "精致色稿（智识）",
                    "智识之钥（智识）",
                    "天外乐章（同谐）",
                    "群星乐章（同谐）",
                    "焚天之魔（虚无）",
                    "沉沦黑曜（虚无）",
                    "阿赖耶华（记忆）",
                    "《绒绒号》典藏版合集（欢愉）"
                },
                MaxSingleTimes = 24
            },

            new(AddTaskItem)
            {
                Title = "凝滞虚影",
                Id = "stagnant_shadow",
                Cost = 30,
                Levels = new[]
                {
                    "---选择副本---",
                    "侵略凝块（物理）",
                    "星际和平工作证（物理）",
                    "幽府通令（物理）",
                    "铁狼碎齿（物理）",
                    "明辉日珥（火）",
                    "忿火之心（火）",
                    "过热钢刀（火）",
                    "恒温晶壳（火）",
                    "海妖残鰭（冰）",
                    "冷藏梦箱（冰）",
                    "苦寒晶壳（冰）",
                    "风雪之角（冰）",
                    "狂雷扫弦（雷）",
                    "兽馆之钉（雷）",
                    "炼形者雷枝（雷）",
                    "往日之影的雷冠（雷）",
                    "暮辉烬蕾（风）",
                    "一杯酪酊的时代（风）",
                    "无人遗垢（风）",
                    "暴风之眼（风）",
                    "暗帷月华（量子）",
                    "炙梦喷枪（量子）",
                    "苍猿之钉（量子）",
                    "虚幻铸铁（量子）",
                    "纷争前兆（虚数）",
                    "一曲和弦的幻景（虚数）",
                    "镇灵敕符（虚数）",
                    "往日之影的金饰（虚数）"
                },
                MaxSingleTimes = 8
            },

            new(AddTaskItem)
            {
                Title = "侵蚀隧洞",
                Id = "caver_of_corrosion",
                Cost = 40,
                Levels = new[]
                {
                    "---选择副本---",
                    "魔占之径（魔法少女/卜者）",
                    "隐救之径（救世主/隐士）",
                    "雳勇之径（女武神/船长）",
                    "弦歌之径（英豪/诗人）",
                    "迷识之径（司铎套/学者套）",
                    "勇骑之径（铁骑套/勇烈套）",
                    "梦潜之径（死水/钟表匠）",
                    "幽冥之径（大公/幽囚）",
                    "药使之径（莳者/信使）",
                    "野焰之径（火匠/废土客）",
                    "圣颂之径（圣骑/乐队）",
                    "睿智之径（铁卫/量子套）",
                    "漂泊之径（过客/快枪手）",
                    "迅拳之径（拳皇/怪盗）",
                    "霜风之径（冰/风套）"
                },
                MaxSingleTimes = 6
            },

            new(AddTaskItem)
            {
                Title = "历战余响",
                Id = "echo_of_war",
                Cost = 30,
                Levels = new[]
                {
                    "---选择副本---",
                    "铁骸的锈冢",
                    "晨昏的回眸",
                    "心兽的战场",
                    "尘梦的赞礼",
                    "蛀星的旧靥",
                    "不死的神实",
                    "寒潮的落幕",
                    "毁灭的开端"
                },
                MaxSingleTimes = 3,
                CanAutoDetect = false
            }
        ];

    public TopLevel? TopLevelObject { get; set; }

    public bool EnableContextMenu => SelectedTaskItem is not null;

    public int CurrencyWarsModeIndex
    {
        get => CurrentConfig.CurrencyWarsMode;
        set
        {
            CurrentConfig.CurrencyWarsMode = value;
            OnPropertyChanged(nameof(IsCwNormalMode));
        }
    }

    public bool IsCwNormalMode => CurrentConfig.CurrencyWarsMode != 2;

    public Cache Cache => _cacheService.Cache;

    [RelayCommand]
    private void SingleTask(string taskName)
    {
        ControlPanelViewModel.StartSingleTask(taskName);
    }

    [RelayCommand]
    private void RefreshStrategies()
    {
        if (!Directory.Exists(PathString.StrategiesDir))
        {
            _commonModel.ShowErrorToast("Error", "未找到攻略文件夹，无法刷新");
            return;
        }
        // 遍历攻略文件夹中的json文件，反序列化成Strategy对象，并更新Cache中的Strategies列表
        var strategies = new List<Strategy>();
        foreach (var file in Directory.GetFiles(PathString.StrategiesDir))
        {
            if (!file.EndsWith(".json")) continue;
            var json = File.ReadAllText(file);
            var strategy = JsonSerializer.Deserialize<Strategy>(json);
            if (strategy is null) continue;
            strategy.FileName = Path.GetFileNameWithoutExtension(file);
            strategies.Add(strategy);
        }
        Cache.Strategies.Clear();
        Cache.Strategies.AddRange(strategies);
        CurrencyWarsStrategyIndex = 0;
    }

    [RelayCommand]
    private async Task SelectedPath()
    {
        if (TopLevelObject is null) return;
        var files = await TopLevelObject.StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions());
        if (files.Count == 0) return;
        CurrentConfig.StartGamePath = files[0].Path.LocalPath;
    }

    [RelayCommand]
    private void DeleteSelectedTaskItem()
    {
        if (SelectedTaskItem is TrailblazePowerTaskItem item) CurrentConfig.TrailblazePowerTaskList.Remove(item);
    }

    private void AddTaskItem(TrailblazePowerTask task)
    {
        if (task.SelectedIndex == 0)
        {
            _commonModel.ShowInfoToast("Info", "请选择副本关卡后再添加任务");
            return;
        }

        CurrentConfig.TrailblazePowerTaskList.Add(new TrailblazePowerTaskItem
        {
            Name = task.Title,
            Id = task.Id,
            Level = task.SelectedIndex,
            LevelName = (task.Levels?.Cast<string>()!).ElementAtOrDefault(task.SelectedIndex) ?? string.Empty,
            Count = task.Count,
            RunTimes = task.RunTimes,
            AutoDetect = task.IsAutoDetect
        });
    }
}

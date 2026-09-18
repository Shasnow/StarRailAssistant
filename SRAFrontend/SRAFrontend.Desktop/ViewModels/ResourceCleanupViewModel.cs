using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Collections.Specialized;
using System.Linq;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using SRAFrontend.Utils;

namespace SRAFrontend.Desktop.ViewModels;

/// <summary>资源清理列表中的单个冗余文件条目</summary>
public class ResourceCleanupItem(string relativePath, long size, bool isSelected, Action selectionChanged)
    : ObservableObject
{
    /// <summary>相对于应用根目录的路径</summary>
    public string RelativePath { get; } = relativePath;

    /// <summary>文件大小（字节）</summary>
    public long Size { get; } = size;

    /// <summary>格式化后的文件大小文本</summary>
    public string SizeText { get; } = ZipUtil.FormatFileSize(size);

    
    public bool IsSelected
    {
        get;
        set
        {
            if (SetProperty(ref field, value)) selectionChanged();
        }
    } = isSelected;
}

/// <summary>资源清理对话框：展示应用目录下不在 MD5 清单中的冗余文件，支持勾选删除</summary>
public partial class ResourceCleanupViewModel : ObservableObject
{
    private readonly string _baseDir;

    public ResourceCleanupViewModel(string baseDir, IReadOnlyList<RedundantFileInfo> redundantFiles)
    {
        _baseDir = baseDir;
        foreach (var file in redundantFiles)
            Files.Add(new ResourceCleanupItem(file.RelativePath, file.Size, true, RefreshStatistics));
        Files.CollectionChanged += OnFilesChanged;
        RefreshStatistics();
    }

    public ObservableCollection<ResourceCleanupItem> Files { get; } = [];

    /// <summary>全选/全不选（部分选中时显示未勾选，点击即全选）</summary>
    public bool IsAllSelected
    {
        get => Files.Count > 0 && Files.All(f => f.IsSelected);
        set
        {
            foreach (var file in Files) file.IsSelected = value;
            OnPropertyChanged();
            RefreshStatistics();
        }
    }

    /// <summary>选中文件的统计摘要（数量与大小）</summary>
    [ObservableProperty]
    private string _selectedSummary = "";

    /// <summary>删除是否进行中（用于显示忙碌状态）</summary>
    [ObservableProperty]
    private bool _isDeleting;

    /// <summary>删除当前勾选的文件，返回（删除数、释放字节数、失败文件列表）</summary>
    public async Task<(int DeletedCount, long FreedBytes, IReadOnlyList<string> FailedFiles)> DeleteSelectedAsync()
    {
        var selected = Files.Where(f => f.IsSelected).Select(f => f.RelativePath).ToList();
        IsDeleting = true;
        try
        {
            return await Task.Run(() => ZipUtil.DeleteFiles(_baseDir, selected));
        }
        finally
        {
            IsDeleting = false;
        }
    }

    private void RefreshStatistics()
    {
        var selectedCount = Files.Count(f => f.IsSelected);
        var selectedSize = Files.Where(f => f.IsSelected).Sum(f => f.Size);
        var totalSize = Files.Sum(f => f.Size);
        SelectedSummary =
            $"已选 {selectedCount}/{Files.Count} 个，共 {ZipUtil.FormatFileSize(selectedSize)}（冗余合计 {ZipUtil.FormatFileSize(totalSize)}）";
        OnPropertyChanged(nameof(IsAllSelected));
    }

    private void OnFilesChanged(object? sender, NotifyCollectionChangedEventArgs e)
    {
        RefreshStatistics();
    }
}

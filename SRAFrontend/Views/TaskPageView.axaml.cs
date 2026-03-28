using System.Collections.Generic;
using System.Linq;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Threading;
using SRAFrontend.ViewModels;
using SRAFrontend.Views.TaskViews;

namespace SRAFrontend.Views;

public partial class TaskPageView : UserControl
{
    private readonly Dictionary<string, UserControl> _viewCache = [];

    public TaskPageView()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        if (DataContext is not TaskPageViewModel viewModel) return;

        viewModel.TopLevelObject = TopLevel.GetTopLevel(this);

        _viewCache["StartGameTask"] = new StartGameView { DataContext = viewModel };
        _viewCache["TrailblazePowerTask"] = new TrailblazePowerView { DataContext = viewModel };
        _viewCache["ReceiveRewardsTask"] = new ReceiveRewardsView { DataContext = viewModel };
        _viewCache["CosmicStrifeTask"] = new CosmicStrife { DataContext = viewModel };
        _viewCache["MissionAccomplishTask"] = new MissionAccomplishView { DataContext = viewModel };

        viewModel.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName == nameof(viewModel.OrderedTabKeys))
                // 延迟执行，避免在按钮事件回调中直接清空控件树导致崩溃
                Dispatcher.UIThread.Post(() => RebuildTabs(viewModel));
        };

        RebuildTabs(viewModel);
    }

    private void RebuildTabs(TaskPageViewModel viewModel)
    {
        var tabControl = this.Find<TabControl>("MainTabControl");
        if (tabControl == null) return;

        var selectedKey = (tabControl.SelectedItem as TabItem)?.Tag as string;
        var newOrder = viewModel.OrderedTabKeys;

        // 增量更新：先确保所有 TabItem 存在，再按新顺序重排，不 Clear
        // 1. 建立 key → TabItem 的映射
        var existingItems = new Dictionary<string, TabItem>();
        foreach (TabItem item in tabControl.Items)
            if (item.Tag is string key)
                existingItems[key] = item;

        // 2. 添加缺少的 TabItem
        foreach (var key in newOrder)
        {
            if (existingItems.ContainsKey(key)) continue;
            if (!_viewCache.TryGetValue(key, out var view)) continue;
            var header = KeyToHeader(key);
            var newItem = new TabItem { Header = header, Content = view, Tag = key };
            existingItems[key] = newItem;
            tabControl.Items.Add(newItem);
        }

        // 3. 移除不在 newOrder 中的 TabItem
        var toRemove = existingItems.Keys.Except(newOrder).ToList();
        foreach (var key in toRemove)
        {
            tabControl.Items.Remove(existingItems[key]);
            existingItems.Remove(key);
        }

        // 4. 按 newOrder 调整顺序（移动 TabItem 位置）
        for (var i = 0; i < newOrder.Count; i++)
        {
            var key = newOrder[i];
            if (!existingItems.TryGetValue(key, out var item)) continue;
            var currentIdx = tabControl.Items.IndexOf(item);
            if (currentIdx == i) continue;
            tabControl.Items.Remove(item);
            tabControl.Items.Insert(i, item);
        }

        // 5. 恢复选中
        if (selectedKey != null && existingItems.TryGetValue(selectedKey, out var selected))
            tabControl.SelectedItem = selected;
    }

    private static string KeyToHeader(string key) => key switch
    {
        "StartGameTask" => Localization.Resources.StartGameText,
        "TrailblazePowerTask" => Localization.Resources.TrailblazePowerText,
        "ReceiveRewardsTask" => Localization.Resources.ReceiveRewardsText,
        "CosmicStrifeTask" => Localization.Resources.CosmicStrifeText,
        "MissionAccomplishTask" => Localization.Resources.InTheEndText,
        _ => key
    };
}

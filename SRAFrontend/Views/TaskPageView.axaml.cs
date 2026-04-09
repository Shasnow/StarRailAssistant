using System;
using Avalonia;
using Avalonia.Animation;
using Avalonia.Animation.Easings;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Styling;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Views;

public partial class TaskPageView : UserControl
{
    private TaskOrderItem? _dragItem;
    private bool _isDragging;
    private double _dragStartX;
    private ItemsControl? _tabHeaderList; // 缓存引用，避免每次 FindControl

    public TaskPageView()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);
        if (DataContext is not TaskPageViewModel viewModel) return;
        var topLevel = TopLevel.GetTopLevel(this);
        viewModel.TopLevelObject = topLevel;

        // 在 OnLoaded 里直接找到 ItemsControl 并缓存
        _tabHeaderList = this.FindControl<ItemsControl>("TabHeaderList");
    }

    // 重写 OnPointerMoved：UserControl 级别，无视子控件是否处理
    protected override void OnPointerMoved(PointerEventArgs e)
    {
        base.OnPointerMoved(e);

        if (_dragItem == null) return;
        if (DataContext is not TaskPageViewModel vm) return;

        var currentX = e.GetPosition(this).X;
        if (!_isDragging && Math.Abs(currentX - _dragStartX) < 8) return;
        _isDragging = true;

        var tabList = _tabHeaderList;
        if (tabList == null) return;

        var posInList = e.GetPosition(tabList);
        int targetIndex = -1;
        for (int i = 0; i < vm.TaskOrderList.Count; i++)
        {
            var container = tabList.ContainerFromIndex(i) as Control;
            if (container == null) continue;
            var topLeft = container.TranslatePoint(new Point(0, 0), tabList);
            if (topLeft == null) continue;
            var rect = new Rect(topLeft.Value, container.Bounds.Size);
            if (posInList.X >= rect.Left && posInList.X <= rect.Right)
            {
                targetIndex = i;
                break;
            }
        }

        int currentIndex = vm.TaskOrderList.IndexOf(_dragItem);
        if (targetIndex >= 0 && targetIndex != currentIndex)
        {
            AnimateDisplace(tabList, targetIndex, currentIndex);
            vm.MoveTaskToIndex(_dragItem, targetIndex);
        }
    }

    // 重写 OnPointerReleased：UserControl 级别
    protected override void OnPointerReleased(PointerReleasedEventArgs e)
    {
        base.OnPointerReleased(e);

        if (_dragItem == null) return;
        if (DataContext is not TaskPageViewModel vm) return;

        if (!_isDragging)
            vm.SelectTask(_dragItem.ClassName);

        e.Pointer.Capture(null);
        _dragItem = null;
        _isDragging = false;
    }

    // Border 上的 PointerPressed：开始拖拽，捕获到 UserControl
    internal void TabHeader_PointerPressed(object? sender, PointerPressedEventArgs e)
    {
        if (DataContext is not TaskPageViewModel vm) return;
        if (sender is not Control card) return;
        var item = card.DataContext as TaskOrderItem;
        if (item == null || item.IsFixed) return;

        _dragItem = item;
        _isDragging = false;
        _dragStartX = e.GetPosition(this).X;
        // 捕获到 UserControl，后续 OnPointerMoved/OnPointerReleased 一定能收到
        e.Pointer.Capture(this);
        e.Handled = true;
    }

    // 固定任务标签点击
    internal void AddCustomTask_PointerPressed(object? sender, Avalonia.Input.PointerPressedEventArgs e)
    {
        if (DataContext is not TaskPageViewModel vm) return;
        vm.AddCustomTaskCommand.Execute(null);
        e.Handled = true;
    }

    internal void FixedTabHeader_PointerPressed(object? sender, PointerPressedEventArgs e)
    {
        if (DataContext is not TaskPageViewModel vm) return;
        if (sender is not Control card) return;
        var item = card.DataContext as TaskOrderItem;
        if (item != null) vm.SelectTask(item.ClassName);
        e.Handled = true;
    }

    // axaml 里注册的占位方法（保留避免编译错误）
    internal void UserControl_PointerMoved(object? sender, PointerEventArgs e) { }
    internal void UserControl_PointerReleased(object? sender, PointerReleasedEventArgs e) { }

    private void AnimateDisplace(ItemsControl tabList, int targetIndex, int fromIndex)
    {
        var container = tabList.ContainerFromIndex(targetIndex) as Control;
        if (container == null) return;

        double direction = fromIndex < targetIndex ? -1.0 : 1.0;
        container.RenderTransform = new TranslateTransform(0, 0);

        var animation = new Animation
        {
            Duration = TimeSpan.FromMilliseconds(140),
            Easing = new CubicEaseOut(),
            Children =
            {
                new KeyFrame
                {
                    Cue = new Cue(0),
                    Setters = { new Setter(TranslateTransform.XProperty, direction * 28.0) }
                },
                new KeyFrame
                {
                    Cue = new Cue(1),
                    Setters = { new Setter(TranslateTransform.XProperty, 0.0) }
                }
            }
        };
        _ = animation.RunAsync(container);
    }
}

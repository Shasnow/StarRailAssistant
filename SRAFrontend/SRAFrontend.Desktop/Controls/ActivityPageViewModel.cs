using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using Avalonia.Media;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SRAFrontend.Desktop.ViewModels;
using SRAFrontend.Models;
using SRAFrontend.Services;

namespace SRAFrontend.Desktop.Controls;

public partial class ActivityPageViewModel(ActivityService activityService) : ViewModelBase
{
    private List<GameActivityInfo> _allActivities = [];
    [ObservableProperty] private DateTime _displayDate = DateTime.Today;
    [ObservableProperty] private bool _isLoading;

    [ObservableProperty] private DateTime? _selectedDate;
    [ObservableProperty] private ObservableCollection<ActivityItemViewModel> _selectedDateActivities = [];
    [ObservableProperty] private string _versionName = "";
    [ObservableProperty] private string _versionNumber = "";
    [ObservableProperty] private string _versionRemaining = "";
    [ObservableProperty] private string _versionTimeRange = "";

    [RelayCommand]
    private async Task LoadAsync()
    {
        if (IsLoading) return;
        IsLoading = true;

        var info = await activityService.GetVersionActivitiesAsync();
        if (info == null)
        {
            IsLoading = false;
            return;
        }

        VersionNumber = info.Version;
        VersionName = info.VersionName;

        var start = DateTime.Parse(info.StartTime);
        var end = DateTime.Parse(info.EndTime);
        VersionTimeRange = $"{start:MM/dd HH:mm} - {end:MM/dd HH:mm}";

        var remaining = (int)(end - DateTime.Now).TotalDays;
        VersionRemaining = remaining > 0 ? $"剩余 {remaining} 天" : "已结束";

        _allActivities = info.Activities?.ToList() ?? [];

        var today = DateTime.Today;
        SelectedDate = today >= start && today <= end ? today : start;
        DisplayDate = SelectedDate.Value;

        IsLoading = false;
    }

    partial void OnSelectedDateChanged(DateTime? value)
    {
        UpdateSelectedDateActivities(value);
    }

    private void UpdateSelectedDateActivities(DateTime? date)
    {
        SelectedDateActivities.Clear();
        if (date == null) return;

        foreach (var act in _allActivities)
        {
            var start = DateTime.Parse(act.StartTime).Date;
            var end = DateTime.Parse(act.EndTime).Date;
            if (date >= start.AddDays(-7) && date <= end)
                SelectedDateActivities.Add(new ActivityItemViewModel(act, date.Value));
        }
    }
}

public class ActivityItemViewModel : ViewModelBase
{
    private static readonly IBrush AbundantBrush = MakeBrush(76, 175, 80);
    private static readonly IBrush ModerateBrush = MakeBrush(255, 193, 7);
    private static readonly IBrush UrgentBrush = MakeBrush(244, 67, 54);
    private static readonly IBrush InactiveBrush = MakeBrush(158, 158, 158);

    public ActivityItemViewModel(GameActivityInfo info, DateTime selectedDate)
    {
        Name = info.Name;
        Description = info.Description;
        DescriptionPreview = Description.Length > 25 ? Description[..25] + "..." : Description;
        var start = DateTime.Parse(info.StartTime);
        var end = DateTime.Parse(info.EndTime);
        TimeRange = $"{start:MM/dd HH:mm} - {end:MM/dd HH:mm}";

        if (selectedDate < start)
        {
            var days = (int)(start - selectedDate).TotalDays;
            Status = "未开始";
            Countdown = days > 0 ? $"{days}天后开始" : "即将开始";
            StatusBrush = InactiveBrush;
        }
        else if (selectedDate > end)
        {
            Status = "已结束";
            Countdown = $"已结束 {(int)(selectedDate - end).TotalDays} 天";
            StatusBrush = InactiveBrush;
        }
        else
        {
            var days = (int)(end - selectedDate).TotalDays;
            Status = "进行中";
            Countdown = days > 0 ? $"剩余 {days} 天" : "即将结束";
            StatusBrush = days > 7
                ? AbundantBrush
                : days > 3
                    ? ModerateBrush
                    : UrgentBrush;
        }
    }

    public string Name { get; }
    public string Description { get; }
    public string DescriptionPreview { get; }
    public bool HasDescription => !string.IsNullOrWhiteSpace(Description);
    public string TimeRange { get; }
    public string Status { get; }
    public string Countdown { get; }
    public IBrush StatusBrush { get; }

    private static IBrush MakeBrush(byte r, byte g, byte b)
    {
        return new SolidColorBrush(new Color(0x55, r, g, b));
    }
}
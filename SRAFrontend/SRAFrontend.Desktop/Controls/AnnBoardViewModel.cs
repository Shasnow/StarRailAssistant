using System.Collections.Generic;
using System.Linq;
using CommunityToolkit.Mvvm.ComponentModel;
using SRAFrontend.Desktop.ViewModels;
using SRAFrontend.Models;

namespace SRAFrontend.Desktop.Controls;

public partial class AnnBoardViewModel : ViewModelBase
{
    public List<Announcement>? Announcements
    {
        get;
        init
        {
            field = value;
            SelectedAnnouncement = value?.FirstOrDefault();
        }
    }

    public bool IsLoading { get; set; }

    [ObservableProperty] private Announcement? _selectedAnnouncement;

    [ObservableProperty] private string _content = string.Empty;

    partial void OnSelectedAnnouncementChanged(Announcement? value)
    {
        Content = value?.Content ?? string.Empty;
    }
}

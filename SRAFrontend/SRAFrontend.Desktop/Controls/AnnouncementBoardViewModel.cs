using System.Collections.Generic;
using SRAFrontend.Desktop.ViewModels;
using SRAFrontend.Models;

namespace SRAFrontend.Desktop.Controls;

public class AnnouncementBoardViewModel : ViewModelBase
{
    public List<Announcement>? Announcements { get; set; }
    public bool IsLoading { get; set; }
}
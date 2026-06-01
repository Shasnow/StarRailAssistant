using System.Collections.Generic;
using SRAFrontend.Models;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Controls;

public class AnnouncementBoardViewModel:ViewModelBase
{
    public List<Announcement>? Announcements { get; set; }
    public bool IsLoading { get; set; }
}
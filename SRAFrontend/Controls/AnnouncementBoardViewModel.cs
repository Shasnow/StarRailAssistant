using System.Threading.Tasks;
using Avalonia.Collections;
using CommunityToolkit.Mvvm.ComponentModel;
using SRAFrontend.Models;
using SRAFrontend.Services;
using SRAFrontend.ViewModels;

namespace SRAFrontend.Controls;

public partial class AnnouncementBoardViewModel:ViewModelBase
{
    [ObservableProperty] private IAvaloniaList<Announcement>? _announcements;
    private readonly AnnouncementService? _announcementService;
    [ObservableProperty] private bool _isLoading;

    public AnnouncementBoardViewModel()
    // Design-time constructor
    {
        _announcements=new AvaloniaList<Announcement>
        {
            new()
            {
                Title = "欢迎使用 SRA 前端！",
                Content = "### SRA随机标题创意征集令！\n你是否已发现，每次启动SRA时，那变幻莫测的标题总能带来一丝惊喜？从“启动器启动启动器”的巧妙循环，到“坐和放宽”的幽默调侃，每一个标题都是一次小小的冒险。现在，为了让这份乐趣持续升级，我们特此发起——SRA随机标题创意征集活动！\n\n#### 🎉 参与方式大揭秘：\n- 发挥你的创意：构思一个既有趣又独特的随机标题。\n- 追溯灵感之源：简单说明标题的出处或创意背景，无论是冷笑话、双关妙语、网络热梗，还是一句触动心灵的歌词，皆可成为你的灵感源泉。\n- 一键投稿：将你的创意标题及解释，发送至邮箱 yukikage@qq.com，即可参与活动！\n#### 📝 标题要求小贴士：\n- 精炼至上：标题长度需控制在20个字符以内，简洁明了更吸引人。\n- 内容健康：请确保标题中不包含任何敏感、政治倾向或色情等不适当内容，让创意在正能量的轨道上飞扬。\n#### 🌟 期待你的闪光点：\n我们相信，每个人的心中都藏着无数奇思妙想。现在，是时候让它们闪耀登场了！无论是天马行空的想象，还是贴近生活的幽默，只要你的标题能够触动人心，就有可能成为SRA下一次启动时的亮点！\n\n快来加入我们，一起为SRA的世界增添更多色彩与乐趣吧！期待你的创意风暴，让每一次启动都成为一次难忘的体验！🚀",
            },
            new()
            {
                Title = "新版本发布",
                Content = "SRA 前端 1.0 版本现已发布，包含多项新功能和改进。",
            }
        };
    }
    public AnnouncementBoardViewModel(AnnouncementService announcementService)
    {
        _announcementService = announcementService;
        _ = LoadAnnouncementsAsync();
    }
    
    private async Task LoadAnnouncementsAsync()
    {
        IsLoading = true;
        var result= await _announcementService!.GetAnnouncementsAsync();
        if (result != null)
        {
            Announcements = new AvaloniaList<Announcement>();
            var all = new Announcement { Title = "All" };
            foreach (var announcement in result)
            {
                all.Content+= announcement.Content + "\n\n";
                Announcements.Add(announcement);
            }
            Announcements.Insert(0, all);
        }
        IsLoading = false;
    }
}
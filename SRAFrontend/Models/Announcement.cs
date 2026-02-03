using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace SRAFrontend.Models;

public class Announcement
{
    [JsonPropertyName("title")]
    public string Title { get; set; } = string.Empty;
    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;
}

public class AnnouncementList
{
    [JsonPropertyName("id")]
    public int Id { get; init; }
    [JsonPropertyName("announcements")]
    public List<Announcement> Announcements { get; init; } = [];
}
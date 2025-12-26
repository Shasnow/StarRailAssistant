namespace SRAFrontend.Models;

public class TrailblazePowerTaskItem
{
    public string Name { get; set; } = "";
    public int Level { get; set; }
    public string LevelName { get; set; } = "";
    public int Count { get; set; } = 1;
    public int RunTimes { get; set; }
    public bool AutoDetect { get; set; }
}
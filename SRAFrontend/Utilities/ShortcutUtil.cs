using System.Diagnostics;
using System.IO;

namespace SRAFrontend.Utilities;

public static class ShortcutUtil
{
    // Windows 无依赖方案（调用 VBScript）
    public static bool CreateWindowsShortcut(string shortcutPath, string appExePath)
    {
        var vbsScript = $"""

                                 Set WshShell = WScript.CreateObject("WScript.Shell")
                                 Set shortcut = WshShell.CreateShortcut("{shortcutPath}")
                                 shortcut.TargetPath = "{appExePath}"
                                 shortcut.WorkingDirectory = "{Path.GetDirectoryName(appExePath)}"
                                 shortcut.Save
                             
                         """;
        var vbsPath = Path.Combine(Path.GetTempPath(), "create_shortcut.vbs");
        File.WriteAllText(vbsPath, vbsScript);

        // 执行 VBScript
        using var process = new Process();
        process.StartInfo = new ProcessStartInfo
        {
            FileName = "cscript.exe",
            Arguments = $"/nologo \"{vbsPath}\"",
            UseShellExecute = false,
            CreateNoWindow = true
        };
        process.Start();
        process.WaitForExit();
        File.Delete(vbsPath); // 删除临时脚本

        return File.Exists(shortcutPath);
    }
}
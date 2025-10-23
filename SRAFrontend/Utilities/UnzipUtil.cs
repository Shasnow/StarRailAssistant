using System;
using System.Diagnostics;
using System.IO;

namespace SRAFrontend.utilities;

public static class UnzipUtil
{
    public static void Unzip(string path, string target)
    {
        Process.Start(new ProcessStartInfo
        {
            FileName = "cmd.exe",
            Arguments = $"/C tar -xf \"{path}\" -C \"{target}\"",
            CreateNoWindow = true,
            UseShellExecute = false
        });
        Environment.Exit(0);
    }
}
using System;
using System.Linq;
using System.Management;
using System.Runtime.InteropServices;

namespace SRAFrontend.Utils;

public static class SysInfo
{
    public static string? CpuName
    {
        get
        {
            var cpuName = "Unknown CPU";
            try
            {
                if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows)) return cpuName;
                using var searcher = new ManagementObjectSearcher("SELECT Name FROM Win32_Processor");
                cpuName = searcher.Get().Cast<ManagementObject>().First()["Name"].ToString();
                return cpuName;
            }
            catch (Exception)
            {
                return cpuName;
            }
        }
    }

    public static string? GpuName
    {
        get
        {
            var gpuName = "Unknown GPU";
            try
            {
                if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows)) return gpuName;
                using var searcher = new ManagementObjectSearcher("SELECT Name FROM Win32_VideoController");
                gpuName = searcher.Get().Cast<ManagementObject>().First()["Name"].ToString();
                return gpuName;
            }
            catch (Exception)
            {
                return gpuName;
            }
        }
    }

    public static string Resolution
    {
        get
        {
            var resolution = "Unknown Resolution";
            try
            {
                if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows)) return resolution;
                using var searcher = new ManagementObjectSearcher(
                    "SELECT CurrentHorizontalResolution, CurrentVerticalResolution FROM Win32_VideoController");
                var obj = searcher.Get().Cast<ManagementObject>().First();
                resolution = $"{obj["CurrentHorizontalResolution"]}x{obj["CurrentVerticalResolution"]}";
                return resolution;
            }
            catch (Exception)
            {
                return resolution;
            }
        }
    }
}
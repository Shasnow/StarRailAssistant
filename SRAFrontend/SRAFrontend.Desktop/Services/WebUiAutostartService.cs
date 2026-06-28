using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Services;

namespace SRAFrontend.Desktop.Services;

/// <summary>
/// Starts/stops SRAFrontend.Server from SRA.exe and manages optional logon
/// autostart for remote control.
/// </summary>
/// <remarks>
/// WebUI is intentionally hosted by SRAFrontend.Server instead of a separate
/// resident WebUI executable.  The desktop app only flips user-facing switches:
/// manual start/stop and a Windows scheduled task for logon startup.
/// </remarks>
public class WebUiAutostartService(SettingsService settingsService, ILogger<WebUiAutostartService> logger)
{
    private const string TaskName = "StarRailAssistant WebUI";
    private const int WebUiPort = 5074;
    private static readonly string ServerExecutableName = "SRA-server.exe";

    public bool IsEnabled => settingsService.Settings.Advanced.IsWebUiRemoteAutostartEnabled;

    public async Task ApplyAsync(CancellationToken cancellationToken = default)
    {
        if (!OperatingSystem.IsWindows())
            return;

        if (IsEnabled)
        {
            await RegisterAsync(cancellationToken);
            return;
        }

        await UnregisterAsync(cancellationToken);
    }

    public void StartServer()
    {
        if (!OperatingSystem.IsWindows())
            return;

        // A process name check alone is not enough: a stale/crashed startup can
        // leave no usable listener.  The port probe confirms the service is
        // actually accepting HTTP requests before SRA.exe reports success.
        if (IsServerRunning() && CanConnectToWebUiPort())
        {
            logger.LogInformation("WebUI server is already running.");
            return;
        }

        var serverExe = ResolveServerExecutable();
        var process = Process.Start(new ProcessStartInfo
        {
            FileName = serverExe,
            Arguments = BuildStartArguments(),
            WorkingDirectory = DataPath.AppRoot,
            UseShellExecute = false,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden
        }) ?? throw new InvalidOperationException("无法启动 WebUI 服务进程。");

        if (!WaitForServerReady(process))
            throw new InvalidOperationException("WebUI 服务启动后未监听 5074 端口，请确认端口未被占用。");

        logger.LogInformation("WebUI server started.");
    }

    public void StopServer()
    {
        if (!OperatingSystem.IsWindows())
            return;

        foreach (var process in Process.GetProcessesByName(Path.GetFileNameWithoutExtension(ServerExecutableName)))
        {
            try
            {
                process.Kill();
                logger.LogInformation("WebUI server stopped: {ProcessId}", process.Id);
            }
            catch (Exception ex)
            {
                logger.LogWarning(ex, "Failed to stop WebUI server: {ProcessId}", process.Id);
            }
            finally
            {
                process.Dispose();
            }
        }
    }

    public bool IsServerRunning()
    {
        return Process.GetProcessesByName(Path.GetFileNameWithoutExtension(ServerExecutableName)).Length > 0;
    }

    private async Task RegisterAsync(CancellationToken cancellationToken)
    {
        var serverExe = ResolveServerExecutable();

        var args = BuildStartArguments();
        // Scheduled Task is used instead of a Startup-folder shortcut because
        // SRA-cli needs administrator privileges for reliable automation.  The
        // task runs only for the current interactive user and ignores duplicate
        // instances so repeated SRA launches do not spawn multiple servers.
        var command =
            "$Action = New-ScheduledTaskAction -Execute '" + EscapePs(serverExe) +
            "' -Argument '" + EscapePs(args) +
            "' -WorkingDirectory '" + EscapePs(DataPath.AppRoot) +
            "'; " +
            "$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME; " +
            "$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest; " +
            "$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit 0; " +
            "Register-ScheduledTask -TaskName '" + EscapePs(TaskName) +
            "' -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description 'StarRailAssistant WebUI autostart' -Force | Out-Null";
        await RunPowerShellAsync(command, cancellationToken);
        logger.LogInformation("WebUI autostart task registered.");
    }

    private async Task UnregisterAsync(CancellationToken cancellationToken)
    {
        var command =
            "if (Get-ScheduledTask -TaskName '" + EscapePs(TaskName) + "' -ErrorAction SilentlyContinue) { " +
            "Unregister-ScheduledTask -TaskName '" + EscapePs(TaskName) + "' -Confirm:$false }";
        await RunPowerShellAsync(command, cancellationToken);
        logger.LogInformation("WebUI autostart task removed.");
    }

    private static string BuildStartArguments()
    {
        // The server listens on 0.0.0.0 so phones or tunneling tools can reach it
        // through the same port.  Token auth is still required by the server.
        return $"--webui --urls=http://0.0.0.0:{WebUiPort} --WebUi:Enabled=true --WebUi:RemoteAccess=true";
    }

    private static string ResolveServerExecutable()
    {
        var serverExe = Path.Combine(DataPath.AppRoot, ServerExecutableName);
        if (File.Exists(serverExe))
            return serverExe;

        // The optional packaging model keeps ServerDLC/WebUI outside the main
        // zip.  This explicit error points users to the missing optional server
        // package instead of failing later with a generic process-start error.
        throw new FileNotFoundException(
            $"找不到 {ServerExecutableName}。请先将 ServerDLC 包解压到 SRA 根目录，或使用包含服务端的完整包。",
            serverExe);
    }

    private static bool WaitForServerReady(Process process)
    {
        var deadline = DateTime.UtcNow.AddSeconds(8);
        while (DateTime.UtcNow < deadline)
        {
            if (process.HasExited)
                return false;

            if (CanConnectToWebUiPort())
                return true;

            Thread.Sleep(250);
        }

        return !process.HasExited && CanConnectToWebUiPort();
    }

    private static bool CanConnectToWebUiPort()
    {
        try
        {
            using var client = new TcpClient();
            var connectTask = client.ConnectAsync("127.0.0.1", WebUiPort);
            return connectTask.Wait(TimeSpan.FromMilliseconds(300)) && client.Connected;
        }
        catch
        {
            return false;
        }
    }

    private static string EscapePs(string value) => value.Replace("'", "''");

    private static async Task RunPowerShellAsync(string script, CancellationToken cancellationToken)
    {
        // PowerShell is used only for the Task Scheduler cmdlets.  Keeping the
        // script construction here avoids adding another dependency or requiring
        // users to run a separate installer step.
        var psi = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = $"-NoProfile -ExecutionPolicy Bypass -Command \"{script.Replace("\"", "\\\"")}\"",
            UseShellExecute = false,
            CreateNoWindow = true,
            WorkingDirectory = DataPath.AppRoot
        };

        using var process = Process.Start(psi) ?? throw new InvalidOperationException("无法启动 PowerShell。");
        await process.WaitForExitAsync(cancellationToken);
        if (process.ExitCode != 0)
            throw new InvalidOperationException($"PowerShell 执行失败，退出码: {process.ExitCode}");
    }
}

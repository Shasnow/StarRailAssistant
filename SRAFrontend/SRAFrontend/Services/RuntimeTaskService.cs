using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using SRAFrontend.Data;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

/// <summary>
/// Reads and writes the runtime coordination files produced by
/// SRACore/runtime/shared_runtime.py.
/// </summary>
/// <remarks>
/// This service is shared by the desktop frontend and the ASP.NET server.  It is
/// intentionally file-based because a task may be started by SRA.exe, WebUI, or
/// SRA-cli directly.  Reading the common session file gives both frontends a
/// consistent view of task state without forcing every user to run a WebUI
/// background process.
/// </remarks>
public class RuntimeTaskService
{
    private static readonly JsonSerializerOptions JsonOptions = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase, WriteIndented = true };
    private static readonly TimeSpan ActiveHeartbeatWindow = TimeSpan.FromSeconds(10);

    public RuntimeTaskStatus GetStatus()
    {
        var session = ReadSession();
        if (session is null)
            return new RuntimeTaskStatus { Detail = "no-session" };

        var lastHeartbeat = FromUnix(session.LastHeartbeatUnix);
        var startedAt = FromUnix(session.StartedAtUnix);
        var heartbeatAge = lastHeartbeat is null ? TimeSpan.MaxValue : DateTimeOffset.UtcNow - lastHeartbeat.Value;
        var processAlive = IsProcessAlive(session.Pid);
        var stateRunning = session.State is "running" or "stopping";
        // A task is active only when the session says it is running, the owning
        // process still exists, and the heartbeat is fresh.  This combination
        // prevents a crashed CLI from being shown as running forever.
        var running = stateRunning && processAlive && heartbeatAge <= ActiveHeartbeatWindow;

        return new RuntimeTaskStatus
        {
            Running = running,
            Pid = session.Pid > 0 ? session.Pid : null,
            SessionId = session.SessionId,
            State = running ? session.State : NormalizeInactiveState(session.State, processAlive, heartbeatAge),
            Owner = session.Owner,
            Mode = session.Mode,
            TaskName = session.TaskName,
            ConfigNames = session.ConfigNames,
            StartedAt = startedAt,
            LastHeartbeat = lastHeartbeat,
            Detail = running ? "active-session" : "inactive-session"
        };
    }

    public bool IsRunning() => GetStatus().Running;

    public bool RequestStop(string source)
    {
        if (!GetStatus().Running)
            return false;

        Directory.CreateDirectory(DataPath.RuntimeDir);
        // Stop is cooperative: the task loop polls this file and exits through
        // its normal cleanup path.  We avoid killing the process here so SRA can
        // restore game/window state and write a terminal session state.
        var payload = new
        {
            source,
            requestedAt = DateTimeOffset.Now.ToString("O"),
            requestedAtUnix = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0
        };
        var tempPath = DataPath.RuntimeStopRequest + ".tmp";
        File.WriteAllText(tempPath, JsonSerializer.Serialize(payload, JsonOptions));
        File.Move(tempPath, DataPath.RuntimeStopRequest, true);
        return true;
    }

    public RuntimeTaskSession? ReadSession()
    {
        try
        {
            if (!File.Exists(DataPath.RuntimeSessionJson))
                return null;
            var json = File.ReadAllText(DataPath.RuntimeSessionJson);
            return JsonSerializer.Deserialize<RuntimeTaskSession>(json);
        }
        catch
        {
            return null;
        }
    }

    private static bool IsProcessAlive(int pid)
    {
        if (pid <= 0) return false;
        try
        {
            using var process = Process.GetProcessById(pid);
            return !process.HasExited;
        }
        catch
        {
            return false;
        }
    }

    private static DateTimeOffset? FromUnix(double value)
    {
        if (value <= 0) return null;
        try
        {
            var milliseconds = checked((long)(value * 1000));
            return DateTimeOffset.FromUnixTimeMilliseconds(milliseconds);
        }
        catch
        {
            return null;
        }
    }

    private static string NormalizeInactiveState(string state, bool processAlive, TimeSpan heartbeatAge)
    {
        // Preserve explicit terminal states from the Python side, but label
        // ambiguous stale sessions so UI callers can show why a task is no
        // longer considered active.
        if (!processAlive) return state is "completed" or "stopped" or "failed" ? state : "exited";
        if (heartbeatAge > ActiveHeartbeatWindow) return "stale";
        return string.IsNullOrWhiteSpace(state) ? "idle" : state;
    }
}

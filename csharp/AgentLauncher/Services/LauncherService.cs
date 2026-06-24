using System.Collections.Concurrent;
using System.Diagnostics;

namespace AgentLauncher.Services;

/// <summary>
/// Launch Claude Code or Hermes in Windows Terminal with tracking PIDs.
/// </summary>
public static class LauncherService
{
    private static readonly string ClaudePath =
        @"C:\Users\Lorien\.local\bin\claude.exe";
    // --dangerously-skip-permissions is intentional: user's own agent in user-owned dirs.
    // Remove this flag if you need interactive per-action permission approvals.
    private static readonly string ClaudeArgs =
        "--dangerously-skip-permissions";
    private static readonly string HermesPath =
        @"C:\Users\Lorien\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe";

    /// <summary>
    /// PIDs of Windows Terminal processes launched by us (for pop-to-front).
    /// </summary>
    public static readonly ConcurrentDictionary<int, bool> LaunchedPids = new();

    /// <summary>
    /// Escape a value for safe use inside a PowerShell single-quoted string.
    /// In PowerShell, single quotes inside a single-quoted string are doubled.
    /// </summary>
    private static string PsEscape(string value) => value.Replace("'", "''");

    /// <summary>
    /// Launch an executable in a given directory via Windows Terminal.
    /// All user-controlled values are escaped to prevent PowerShell injection.
    /// </summary>
    public static bool LaunchInTerminal(string dirPath, string exePath, string args, string title)
    {
        if (!Directory.Exists(dirPath)) return false;

        try
        {
            // Write a temporary PowerShell script — all user paths escaped
            var tempPath = Path.Combine(Path.GetTempPath(), $"launch_{Guid.NewGuid():N}.ps1");
            var script = $"cd '{PsEscape(dirPath)}'; & '{PsEscape(exePath)}' {args}";
            File.WriteAllText(tempPath, script, System.Text.Encoding.UTF8);

            var psi = new ProcessStartInfo
            {
                FileName = "wt",
                Arguments = $"--title \"{title}\" pwsh -NoExit -File \"{tempPath}\"",
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden
            };

            var proc = Process.Start(psi);
            if (proc != null)
            {
                LaunchedPids[proc.Id] = true;
            }

            // Cleanup temp script after a few seconds
            _ = Task.Run(async () =>
            {
                await Task.Delay(3000);
                try { File.Delete(tempPath); } catch { }
            });

            return true;
        }
        catch { return false; }
    }

    /// <summary>
    /// Launch Claude Code in the given directory.
    /// </summary>
    public static bool LaunchClaude(string dirPath)
    {
        return LaunchInTerminal(dirPath, ClaudePath, ClaudeArgs, "Claude Code");
    }

    /// <summary>
    /// Launch Hermes in the given directory.
    /// </summary>
    public static bool LaunchHermes(string dirPath)
    {
        return LaunchInTerminal(dirPath, HermesPath, "", "Hermes");
    }

    /// <summary>
    /// Bring the terminal window matching one of our launched PIDs to the front.
    /// </summary>
    public static void BringTerminalToFront()
    {
        try
        {
            var pids = new HashSet<int>(LaunchedPids.Keys);
            var hwnd = Helpers.NativeMethods.FindTerminalWindow(pids);
            if (hwnd.HasValue)
            {
                Helpers.NativeMethods.ShowWindow(hwnd.Value, Helpers.NativeMethods.SW_RESTORE);
                Helpers.NativeMethods.SetForegroundWindow(hwnd.Value);
            }
        }
        catch { }
    }
}

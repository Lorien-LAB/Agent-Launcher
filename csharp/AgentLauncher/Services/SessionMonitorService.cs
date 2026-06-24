using System.Diagnostics;
using System.Text.Json;
using AgentLauncher.Models;

namespace AgentLauncher.Services;

/// <summary>
/// Background monitoring engine — reads ~/.claude/sessions/ and transcript JSONL files.
/// Port of Python SessionMonitor.
/// </summary>
public class SessionMonitorService
{
    private static readonly string ClaudeDir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".claude");
    private static readonly string SessionsDir =
        Path.Combine(ClaudeDir, "sessions");
    private static readonly string ProjectsDir =
        Path.Combine(ClaudeDir, "projects");

    // Max context per model
    private static readonly Dictionary<string, int> ModelContext = new()
    {
        ["deepseek-v4-pro"] = 1_000_000,
        ["deepseek-v4-pro[1m]"] = 1_000_000,
        ["claude-sonnet-4-20250514"] = 200_000,
        ["claude-opus-4-20250514"] = 200_000,
        ["claude-opus-4-8"] = 200_000,
        ["claude-haiku-4-5-20251001"] = 200_000,
    };

    // Token pricing (USD per 1M)
    private static readonly Dictionary<string, (double input, double output)> TokenPrice = new()
    {
        ["deepseek-v4-pro"] = (0.55, 2.19),
    };

    private readonly Thread _thread;
    private readonly object _lock = new();
    private readonly Dictionary<string, (int input, int output)> _sessionTotals = new();
    private AggregateStats _stats = new();
    private bool _running;

    public event Action<AggregateStats>? OnUpdate;

    public AggregateStats Stats
    {
        get { lock (_lock) return _stats; }
    }

    public SessionMonitorService()
    {
        _thread = new Thread(RunLoop)
        {
            Name = "session-monitor",
            IsBackground = true
        };
    }

    public void Start()
    {
        _running = true;
        _thread.Start();
    }

    public void Stop()
    {
        _running = false;
    }

    public AggregateStats Scan()
    {
        var sessions = new List<SessionSnapshot>();
        int totalIn = 0, totalOut = 0;
        double totalCost = 0;

        if (!Directory.Exists(SessionsDir))
        {
            var agg = new AggregateStats();
            lock (_lock) _stats = agg;
            OnUpdate?.Invoke(agg);
            return agg;
        }

        string[] pidFiles;
        try { pidFiles = Directory.GetFiles(SessionsDir, "*.json"); }
        catch { pidFiles = Array.Empty<string>(); }

        foreach (var path in pidFiles)
        {
            try
            {
                var json = File.ReadAllText(path, System.Text.Encoding.UTF8);
                using var doc = JsonDocument.Parse(json);
                var root = doc.RootElement;

                var sid = root.TryGetProperty("sessionId", out var sj) ? sj.GetString() ?? "" : "";
                var status = root.TryGetProperty("status", out var ss) ? ss.GetString() ?? "idle" : "idle";
                var cwd = root.TryGetProperty("cwd", out var sc) ? sc.GetString() ?? "" : "";
                var name = root.TryGetProperty("name", out var sn) ? sn.GetString() ?? "" : "";
                var pid = root.TryGetProperty("pid", out var sp) ? sp.GetInt32() : 0;
                var updated = root.TryGetProperty("updatedAt", out var su) ? su.GetInt64() / 1000 : 0L;

                var parts = cwd.Replace('\\', '/').Trim('/').Split('/');
                var shortDir = parts.Length > 0 ? parts[^1] : cwd;
                if (string.IsNullOrEmpty(name)) name = shortDir;

                var snap = new SessionSnapshot
                {
                    SessionId = sid,
                    Pid = pid,
                    Status = status,
                    Cwd = cwd,
                    Name = name,
                    UpdatedAt = updated,
                    ShortDir = shortDir,
                    Model = "?"
                };

                // Find transcript
                var tpath = FindTranscript(sid, cwd);
                if (tpath != null)
                {
                    snap.GitBranch = ReadGitBranch(tpath);
                    snap.SubagentCount = CountSubagents(cwd, sid);
                    (snap.Model, snap.OutputTokens) = ReadLastModelAndOutput(tpath);

                    int peakCtx = ReadMaxContextTokens(tpath);
                    lock (_lock)
                    {
                        if (!_sessionTotals.TryGetValue(sid, out var prev))
                            prev = (0, 0);
                        prev.Item1 = Math.Max(prev.Item1, peakCtx);
                        prev.Item2 = Math.Max(prev.Item2, snap.OutputTokens);
                        _sessionTotals[sid] = prev;
                        snap.InputTokens = prev.Item1;
                        snap.OutputTokens = prev.Item2;
                    }

                    int maxCtx = ModelContext.GetValueOrDefault(snap.Model, 200_000);
                    snap.ContextPct = Math.Round(snap.InputTokens / (double)maxCtx * 100.0, 1);

                    var pricing = TokenPrice.GetValueOrDefault(snap.Model, (3.0, 15.0));
                    snap.CostUsd = snap.InputTokens / 1_000_000.0 * pricing.Item1 +
                                   snap.OutputTokens / 1_000_000.0 * pricing.Item2;
                }

                totalIn += snap.InputTokens;
                totalOut += snap.OutputTokens;
                totalCost += snap.CostUsd;
                sessions.Add(snap);
            }
            catch { /* skip broken session files */ }
        }

        // Sort: busy first, then by updatedAt desc
        sessions.Sort((a, b) =>
        {
            int cmp = a.IsBusy.CompareTo(b.IsBusy);
            if (cmp != 0) return cmp; // busy=false sorts after busy=true? No: true(1) > false(0), so we want 0 (busy first)
            // Actually: we want busy first. busy=true → sort key 0, busy=false → sort key 1
            return -a.UpdatedAt.CompareTo(b.UpdatedAt);
        });
        sessions = sessions.OrderBy(s => s.IsBusy ? 0 : 1)
                           .ThenByDescending(s => s.UpdatedAt)
                           .ToList();

        var aggregate = new AggregateStats
        {
            ActiveCount = sessions.Count(s => s.IsBusy),
            IdleCount = sessions.Count(s => !s.IsBusy),
            TotalInput = totalIn,
            TotalOutput = totalOut,
            TotalCost = totalCost,
            Sessions = sessions
        };

        lock (_lock) _stats = aggregate;
        OnUpdate?.Invoke(aggregate);
        return aggregate;
    }

    private void RunLoop()
    {
        while (_running)
        {
            try { Scan(); }
            catch { /* keep running */ }
            Thread.Sleep(3000);
        }
    }

    // ── Helper methods ──

    private static string ProjectPath(string cwd)
    {
        var p = cwd.Replace(":\\", "--").Replace(":/", "--");
        foreach (var ch in new[] { '\\', '/', ' ', '_' })
            p = p.Replace(ch, '-');
        return p;
    }

    private static string? FindTranscript(string sessionId, string cwd)
    {
        var proj = ProjectPath(cwd);
        // Exact match
        var candidate = Path.Combine(ProjectsDir, proj, $"{sessionId}.jsonl");
        if (File.Exists(candidate)) return candidate;

        // Fallback search
        var projDir = Path.Combine(ProjectsDir, proj);
        if (Directory.Exists(projDir))
        {
            foreach (var fn in Directory.GetFiles(projDir, "*.jsonl"))
            {
                if (Path.GetFileName(fn).Contains(sessionId))
                    return fn;
            }
        }
        return null;
    }

    private static int ReadMaxContextTokens(string path)
    {
        int maxVal = 0;
        try
        {
            foreach (var line in File.ReadLines(path, System.Text.Encoding.UTF8))
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                try
                {
                    using var doc = JsonDocument.Parse(line);
                    var root = doc.RootElement;
                    if (root.TryGetProperty("type", out var t) && t.GetString() != "assistant") continue;
                    if (!root.TryGetProperty("message", out var msg)) continue;
                    if (!msg.TryGetProperty("usage", out var usage)) continue;

                    int inp = usage.TryGetProperty("input_tokens", out var it) ? it.GetInt32() : 0;
                    int cr = usage.TryGetProperty("cache_read_input_tokens", out var crt) ? crt.GetInt32() : 0;
                    int cc = usage.TryGetProperty("cache_creation_input_tokens", out var cct) ? cct.GetInt32() : 0;

                    int ctx = inp + (cr == 0 && cc > 0 ? cc : cr);
                    if (ctx > maxVal) maxVal = ctx;
                }
                catch { }
            }
        }
        catch { }
        return maxVal;
    }

    private static (string model, int outputTokens) ReadLastModelAndOutput(string path)
    {
        try
        {
            // Read last 64KB tail
            using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            long size = fs.Length;
            if (size == 0) return ("?", 0);
            fs.Seek(Math.Max(0, size - 65536), SeekOrigin.Begin);
            using var sr = new StreamReader(fs, System.Text.Encoding.UTF8);
            var text = sr.ReadToEnd();
            var lines = text.Trim().Split('\n');
            for (int i = lines.Length - 1; i >= 0; i--)
            {
                var line = lines[i].Trim();
                if (string.IsNullOrEmpty(line)) continue;
                try
                {
                    using var doc = JsonDocument.Parse(line);
                    var root = doc.RootElement;
                    if (root.TryGetProperty("type", out var t) && t.GetString() == "assistant")
                    {
                        var msg = root.GetProperty("message");
                        var model = msg.TryGetProperty("model", out var m) ? m.GetString() ?? "?" : "?";
                        var usage = msg.GetProperty("usage");
                        var output = usage.TryGetProperty("output_tokens", out var o) ? o.GetInt32() : 0;
                        return (model, output);
                    }
                }
                catch { }
            }
        }
        catch { }
        return ("?", 0);
    }

    private static string ReadGitBranch(string path)
    {
        try
        {
            using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            long size = fs.Length;
            if (size < 10) return "";
            fs.Seek(Math.Max(0, size - 4096), SeekOrigin.Begin);
            using var sr = new StreamReader(fs, System.Text.Encoding.UTF8);
            var text = sr.ReadToEnd();
            var lines = text.Trim().Split('\n');
            for (int i = lines.Length - 1; i >= 0; i--)
            {
                var line = lines[i].Trim();
                if (string.IsNullOrEmpty(line)) continue;
                try
                {
                    using var doc = JsonDocument.Parse(line);
                    if (doc.RootElement.TryGetProperty("gitBranch", out var gb))
                    {
                        var branch = gb.GetString() ?? "";
                        if (!string.IsNullOrEmpty(branch))
                            return branch.Replace("HEAD", "");
                    }
                }
                catch { }
            }
        }
        catch { }
        return "";
    }

    private static int CountSubagents(string cwd, string sessionId)
    {
        var proj = ProjectPath(cwd);
        var subDir = Path.Combine(ProjectsDir, proj, sessionId, "subagents");
        if (!Directory.Exists(subDir)) return 0;
        try
        {
            return Directory.GetFiles(subDir, "*.meta.json").Length;
        }
        catch { return 0; }
    }
}

/// <summary>
/// Token/cost formatting helpers — matches Python _fmt_tokens / _fmt_cost.
/// </summary>
public static class Formatting
{
    public static string FmtTokens(int n)
    {
        if (n >= 1_000_000) return $"{n / 1_000_000.0:F1}M";
        if (n >= 1_000) return $"{n / 1_000.0:F1}K";
        return n.ToString();
    }

    public static string FmtCost(double usd)
    {
        if (usd < 0.01) return "<$0.01";
        return $"${usd:F2}";
    }
}

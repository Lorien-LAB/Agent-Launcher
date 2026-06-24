namespace AgentLauncher.Models;

/// <summary>
/// Snapshot of a single Claude Code / Hermes session.
/// Corresponds to Python SessionSnapshot dataclass.
/// </summary>
public class SessionSnapshot
{
    public string SessionId { get; set; } = "";
    public int Pid { get; set; }
    public string Status { get; set; } = "idle";  // "busy" | "idle"
    public string Cwd { get; set; } = "";
    public string Name { get; set; } = "";
    public string Model { get; set; } = "?";
    public int InputTokens { get; set; }
    public int OutputTokens { get; set; }
    public double ContextPct { get; set; }
    public double CostUsd { get; set; }
    public long UpdatedAt { get; set; }
    public string ShortDir { get; set; } = "";
    public string GitBranch { get; set; } = "";
    public int SubagentCount { get; set; }

    public int TotalTokens => InputTokens + OutputTokens;

    public string ModelShort => Model
        .Replace("deepseek-v4-pro", "DSv4")
        .Replace("claude-", "")
        .Replace("deepseek-v4-pro[1m]", "DSv4");

    public bool IsBusy => Status == "busy";
    public bool IsNewlyCompleted { get; set; }
}

/// <summary>
/// Aggregate stats across all sessions.
/// </summary>
public class AggregateStats
{
    public int ActiveCount { get; set; }
    public int IdleCount { get; set; }
    public int TotalInput { get; set; }
    public int TotalOutput { get; set; }
    public double TotalCost { get; set; }
    public List<SessionSnapshot> Sessions { get; set; } = new();

    public int TotalTokens => TotalInput + TotalOutput;
}

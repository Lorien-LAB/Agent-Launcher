"""
Session Monitor — real-time Claude Code token/stats tracker.

Reads ~/.claude/sessions/<pid>.json for active session metadata,
parses transcript JSONL files for per-turn token usage,
and provides aggregated stats for tray display.
"""
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

CLAUDE_DIR = os.path.expanduser("~/.claude")
SESSIONS_DIR = os.path.join(CLAUDE_DIR, "sessions")
PROJECTS_DIR = os.path.join(CLAUDE_DIR, "projects")

# Max context per model (approximate)
MODEL_CONTEXT = {
    "deepseek-v4-pro": 1_000_000,
    "deepseek-v4-pro[1m]": 1_000_000,
    "claude-sonnet-4-20250514": 200_000,
    "claude-opus-4-20250514": 200_000,
    "claude-opus-4-8": 200_000,
    "claude-haiku-4-5-20251001": 200_000,
}

# Token pricing (USD per 1M tokens) — approximate
TOKEN_PRICE = {
    "deepseek-v4-pro": {"input": 0.55, "output": 2.19},
}


def _project_path(cwd: str) -> str:
    """Convert filesystem cwd to .claude projects/ subdirectory name.
    Claude Code encodes: :\\ → --, then \\ / space _ → -
    """
    p = cwd.replace(":\\", "--").replace(":/", "--")
    for ch in ("\\", "/", " ", "_"):
        p = p.replace(ch, "-")
    return p


def _find_transcript(session_id: str, cwd: str) -> Optional[str]:
    """Locate the transcript JSONL file for a session."""
    proj = _project_path(cwd)
    # Try the exact session UUID filename
    candidate = os.path.join(PROJECTS_DIR, proj, f"{session_id}.jsonl")
    if os.path.isfile(candidate):
        return candidate
    # Fallback: search the project dir
    proj_dir = os.path.join(PROJECTS_DIR, proj)
    if os.path.isdir(proj_dir):
        for fn in os.listdir(proj_dir):
            if fn.endswith(".jsonl") and session_id in fn:
                return os.path.join(proj_dir, fn)
    return None


def _read_transcript_totals(path: str) -> tuple:
    """Scan full transcript, return (last_ctx, cumulative_input, cumulative_output, model).

    Context tokens = input_tokens + cache_read_input_tokens.
    Cumulative totals cover every assistant turn (used for cost calculation).
    """
    last_ctx = 0
    last_model = "?"
    total_in = 0
    total_out = 0
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") != "assistant":
                    continue
                u = obj.get("message", {}).get("usage", {})
                inp = u.get("input_tokens", 0) or 0
                cr = u.get("cache_read_input_tokens", 0) or 0
                out = u.get("output_tokens", 0) or 0
                # Context = uncached input + cache-hit tokens
                # (input_tokens excludes cache hits; add them back for total context)
                last_ctx = inp + cr
                total_in += inp
                total_out += out
                m = obj.get("message", {}).get("model", "")
                if m:
                    last_model = m
        return last_ctx, total_in, total_out, last_model
    except (OSError, IOError):
        return 0, 0, 0, "?"



def _read_git_branch(path: str) -> str:
    """Read the gitBranch field from the last few lines of a transcript."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size < 10:
                return ""
            chunk_start = max(0, size - 4096)
            f.seek(chunk_start)
            raw = f.read()
            text = raw.decode("utf-8", errors="ignore")
            for line in reversed(text.strip().split("\n")):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                branch = obj.get("gitBranch", "")
                if branch:
                    return branch
        return ""
    except (OSError, IOError):
        return ""


def _count_subagents(cwd: str, session_id: str) -> int:
    """Count sub-agent meta files under the session's subagents/ directory."""
    proj = _project_path(cwd)
    sub_dir = os.path.join(PROJECTS_DIR, proj, session_id, "subagents")
    if not os.path.isdir(sub_dir):
        return 0
    try:
        return len([f for f in os.listdir(sub_dir) if f.endswith(".meta.json")])
    except OSError:
        return 0



def _fmt_tokens(n: int) -> str:
    """Format token count for display."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _fmt_cost(usd: float) -> str:
    if usd < 0.01:
        return "<$0.01"
    return f"${usd:.2f}"


@dataclass
class SessionSnapshot:
    session_id: str
    pid: int
    status: str          # "busy" | "idle"
    cwd: str
    name: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    context_pct: float = 0.0
    cost_usd: float = 0.0
    updated_at: float = 0.0
    short_dir: str = ""
    git_branch: str = ""
    subagent_count: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class AggregateStats:
    active_count: int = 0
    idle_count: int = 0
    total_input: int = 0
    total_output: int = 0
    total_cost: float = 0.0
    sessions: List[SessionSnapshot] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.total_input + self.total_output


class SessionMonitor:
    """Background thread that periodically scans Claude Code session data."""

    POLL_INTERVAL = 3  # seconds

    def __init__(self):
        self._running = False
        self._stats = AggregateStats()
        self._lock = threading.Lock()
        self._callbacks = []  # list of callable(stats)

    def on_update(self, callback):
        """Register a callback called after each scan with AggregateStats."""
        self._callbacks.append(callback)

    @property
    def stats(self) -> AggregateStats:
        with self._lock:
            return self._stats

    def scan(self) -> AggregateStats:
        sessions = []
        total_in = 0
        total_out = 0
        total_cost = 0.0

        # 1. Read active session PIDs from sessions/
        if not os.path.isdir(SESSIONS_DIR):
            agg = AggregateStats()
            with self._lock:
                self._stats = agg
            self._fire_callbacks()
            return agg

        try:
            pid_files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")]
        except OSError:
            pid_files = []

        for fn in pid_files:
            path = os.path.join(SESSIONS_DIR, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            sid = data.get("sessionId", "")
            status = data.get("status", "idle")
            cwd = data.get("cwd", "")
            name = data.get("name", os.path.basename(cwd) or "?")
            pid = data.get("pid", 0)
            updated = data.get("updatedAt", 0) / 1000.0  # ms → s

            # Short directory label — last segment only
            parts = cwd.replace("\\", "/").strip("/").split("/")
            short = parts[-1] if parts else cwd

            snap = SessionSnapshot(
                session_id=sid, pid=pid, status=status,
                cwd=cwd, name=name, model="?",
                updated_at=updated, short_dir=short,
            )

            # 2. Find transcript, extract tokens, model, git branch
            tpath = _find_transcript(sid, cwd)
            if tpath:
                snap.git_branch = _read_git_branch(tpath).replace("HEAD", "")
                snap.subagent_count = _count_subagents(cwd, sid)

                # One full scan: latest context + cumulative totals + model
                last_ctx, cum_in, cum_out, model = _read_transcript_totals(tpath)
                snap.input_tokens = cum_in
                snap.output_tokens = cum_out
                snap.model = model

                # Context % based on latest turn (not peak), vs model max
                max_ctx = MODEL_CONTEXT.get(snap.model, 200_000)
                snap.context_pct = round(last_ctx / max_ctx * 100, 1) if max_ctx else 0.0

                # Cost from cumulative tokens
                pricing = TOKEN_PRICE.get(snap.model, {"input": 3.0, "output": 15.0})
                snap.cost_usd = (
                    cum_in / 1_000_000 * pricing["input"]
                    + cum_out / 1_000_000 * pricing["output"]
                )

            total_in += snap.input_tokens
            total_out += snap.output_tokens
            total_cost += snap.cost_usd
            sessions.append(snap)

        # Sort: busy first, then by updated_at desc
        sessions.sort(key=lambda s: (0 if s.status == "busy" else 1, -s.updated_at))

        active = sum(1 for s in sessions if s.status == "busy")
        idle = sum(1 for s in sessions if s.status == "idle")

        agg = AggregateStats(
            active_count=active,
            idle_count=idle,
            total_input=total_in,
            total_output=total_out,
            total_cost=total_cost,
            sessions=sessions,
        )

        with self._lock:
            self._stats = agg

        self._fire_callbacks()
        return agg

    def _fire_callbacks(self):
        for cb in self._callbacks:
            try:
                cb(self._stats)
            except Exception:
                pass

    def start(self):
        """Begin background polling."""
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True, name="session-monitor")
        t.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                self.scan()
            except Exception:
                pass
            time.sleep(self.POLL_INTERVAL)

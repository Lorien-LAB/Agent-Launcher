from __future__ import annotations

from dataclasses import dataclass
import os

from launcher_state import LaunchOptions


@dataclass(frozen=True)
class LaunchResult:
    success: bool
    agent_type: str
    terminal_mode: str
    error: str = ""


class LaunchController:
    def __init__(self, launcher, state_store, claude_path, hermes_path, claude_skip_args, logger=None):
        self.launcher = launcher
        self.state_store = state_store
        self.claude_path = claude_path
        self.hermes_path = hermes_path
        self.claude_skip_args = claude_skip_args
        self.logger = logger

    def launch(self, agent_type: str, directory: str, options: LaunchOptions) -> LaunchResult:
        if agent_type not in {"claude", "hermes"}:
            return self._failure(agent_type, options, "unknown agent", directory)
        if not os.path.isdir(directory):
            return self._failure(agent_type, options, "directory not found", directory)

        executable = self.claude_path if agent_type == "claude" else self.hermes_path
        args = self.claude_skip_args if agent_type == "claude" and options.skip_permissions else ""
        title = "Claude Code" if agent_type == "claude" else "Hermes"

        if self.logger:
            self.logger.info("launch requested agent=%s mode=%s cwd=%s", agent_type, options.terminal_mode, directory)

        try:
            success = bool(self.launcher(
                dir_path=directory,
                exe_path=executable,
                args=args,
                title=title,
                terminal_mode=options.terminal_mode,
            ))
        except (OSError, ValueError) as exc:
            return self._failure(agent_type, options, str(exc), directory)

        if not success:
            return self._failure(agent_type, options, "terminal launch failed", directory)

        try:
            self.state_store.record_recent(directory)
        except OSError as exc:
            if self.logger:
                self.logger.warning("recent-directory update failed cwd=%s error=%s", directory, exc)
        return LaunchResult(True, agent_type, options.terminal_mode)

    def _failure(self, agent_type, options, error, directory):
        if self.logger:
            self.logger.warning("launch failed agent=%s mode=%s cwd=%s error=%s", agent_type, options.terminal_mode, directory, error)
        return LaunchResult(False, agent_type, options.terminal_mode, error)

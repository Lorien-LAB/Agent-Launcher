import unittest

from terminal_launch_modes import build_tab_command


class TerminalLaunchModeTests(unittest.TestCase):
    def test_tab_command_targets_active_terminal_window(self):
        command = build_tab_command(
            directory=r"D:\Project",
            title="Claude Code — Project",
            script_path=r"C:\Temp\launch.ps1",
        )
        self.assertEqual(command[:5], ["wt", "-w", "0", "new-tab", "-d"])
        self.assertIn("--suppressApplicationTitle", command)
        self.assertEqual(command[-3:], ["-NoExit", "-File", r"C:\Temp\launch.ps1"])


if __name__ == "__main__":
    unittest.main()

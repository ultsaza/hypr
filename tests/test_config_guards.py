"""Retired update entry points must never move or replace personal settings."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ConfigGuardTests(unittest.TestCase):
    def check_guard(self, script):
        with tempfile.TemporaryDirectory(prefix="hypr-guard-test-") as directory:
            sandbox = Path(directory)
            config = sandbox / ".config/hypr"
            (config / "UserConfigs").mkdir(parents=True)
            sentinel = config / "UserConfigs/personal.lua"
            sentinel.write_text("-- personal settings must survive\n")
            before = sentinel.read_bytes()
            commands = sandbox / "bin"
            commands.mkdir()
            # Notifications are the only UI side effect; filesystem operations
            # remain real, confined to the disposable home used by this test.
            (commands / "notify-send").symlink_to("/usr/bin/true")
            environment = dict(os.environ)
            environment.update(HOME=str(sandbox), PATH=f"{commands}:/usr/bin:/bin")
            environment.pop("HYPRLAND_INSTANCE_SIGNATURE", None)
            environment.pop("WAYLAND_DISPLAY", None)
            result = subprocess.run(
                ["/bin/bash", str(ROOT / "scripts" / script)],
                env=environment,
                input="",
                text=True,
                capture_output=True,
                timeout=5,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(sentinel.is_file(), "guard moved or deleted UserConfigs")
            self.assertEqual(sentinel.read_bytes(), before)
            self.assertFalse((config / "UserConfigsBak").exists())

    def test_user_config_switcher_does_not_move_settings_without_lua_entrypoint(self):
        self.check_guard("UserConfigsSwitcher.sh")

    def test_upstream_update_does_not_replace_settings(self):
        self.check_guard("KooLsDotsUpdate.sh")

    def test_window_rule_update_does_not_replace_settings(self):
        self.check_guard("update_WindowRules.sh")


if __name__ == "__main__":
    unittest.main()

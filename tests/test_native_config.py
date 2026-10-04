"""Load the real configuration and selectable presets without starting a session."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HYPRLAND = shutil.which("Hyprland")


@unittest.skipUnless(HYPRLAND, "Hyprland is required for native config validation")
class NativeConfigTests(unittest.TestCase):
    def verify_config(self, config, preset=False):
        with tempfile.TemporaryDirectory(prefix="hypr-native-test-") as directory:
            runtime = Path(directory)
            if preset:
                # Presets require variables.lua from the repository root even
                # though their own files live in a nested directory.
                wrapper = runtime / "preset.lua"
                wrapper.write_text(
                    f"package.path = {json.dumps(str(ROOT / '?.lua'))} .. ';' .. package.path\n"
                    f"dofile({json.dumps(str(config))})\n"
                )
                config = wrapper
            environment = dict(os.environ)
            environment["XDG_RUNTIME_DIR"] = str(runtime)
            environment.pop("HYPRLAND_INSTANCE_SIGNATURE", None)
            environment.pop("WAYLAND_DISPLAY", None)
            result = subprocess.run(
                [HYPRLAND, "--verify-config", "--config", str(config)],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                timeout=15,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("config ok", output)

    def test_entrypoint_loads_all_required_lua_modules(self):
        self.verify_config(ROOT / "hyprland.lua")

    def test_all_selectable_presets_load(self):
        for folder in ("animations", "Monitor_Profiles"):
            presets = sorted((ROOT / folder).glob("*.lua"))
            self.assertTrue(presets, f"no selectable presets in {folder}")
            for preset in presets:
                with self.subTest(preset=str(preset.relative_to(ROOT))):
                    self.verify_config(preset, preset=True)


if __name__ == "__main__":
    unittest.main()

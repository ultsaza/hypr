#!/usr/bin/env python3
"""Real compositor tests. Missing private IPC or output is a failure."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import unittest


def hyprctl(*args):
    signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not signature or not os.environ.get("HEADLESS_ARTIFACTS"):
        raise AssertionError("No isolated headless session: private instance and artifacts required")
    return subprocess.check_output(
        ["hyprctl", "-i", signature, *args], text=True, timeout=5
    )


def state(name):
    return json.loads(hyprctl("-j", name))


def keys(*tokens):
    subprocess.run(["raw-key", *tokens], check=True, timeout=10)


def wait_for(predicate, description, timeout=8):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {description}; last observation: {last!r}")


class RuntimeSmoke(unittest.TestCase):
    # Catches missing/disabled native headless output or a wrong scale.
    def test_native_headless_output_enabled_at_scale_one(self):
        monitors = json.loads(hyprctl("-j", "monitors"))
        self.assertEqual([item["name"] for item in monitors], ["TEST-1"])
        self.assertEqual(monitors[0]["scale"], 1.0)
        self.assertFalse(monitors[0]["disabled"])

    # Catches failed parsing/loading of the copied production configuration.
    def test_configuration_has_no_errors(self):
        self.assertEqual(hyprctl("configerrors").strip(), "")

    # Catches a virtual keyboard with synthesized keymaps that miss code:11,
    # a missing input delivery path, or a lost production workspace binding.
    def test_raw_evdev_workspace_key_reaches_compositor(self):
        self.assertEqual(json.loads(hyprctl("-j", "activeworkspace"))["id"], 1)
        for code, expected in ((3, 2), (2, 1)):
            keys("+125", f"+{code}", f"-{code}", "-125")
            wait_for(lambda: state("activeworkspace")["id"] == expected,
                     f"raw workspace key reaches workspace {expected}")


class RuntimeDaily(unittest.TestCase):
    """Ordered real scenarios; a failed prerequisite stops dependent actions."""

    def test_daily_keyboard_operations(self):
        artifacts = Path(os.environ["HEADLESS_ARTIFACTS"])
        observations = []
        owned_clients = set()

        def record(scenario, **values):
            observations.append({"scenario": scenario, **values})
            (artifacts / "daily-scenarios.json").write_text(json.dumps(observations, indent=2))
            print(f"SCENARIO {scenario}: {values}", flush=True)

        def active():
            return state("activewindow").get("address")

        def client(address):
            return next((c for c in state("clients") if c["address"] == address), None)

        def launch():
            before = {c["address"] for c in state("clients")}
            keys("+125", "+28", "-28", "-125")

            def new_focused_ghostty():
                new = [c for c in state("clients") if c["address"] not in before
                       and c["class"] == "com.mitchellh.ghostty" and c["mapped"]]
                return new[0] if len(new) == 1 and active() == new[0]["address"] else None

            result = wait_for(new_focused_ghostty, "Super+Enter to launch and focus one mapped Ghostty")
            owned_clients.add(result["address"])
            self.assertEqual({c["address"] for c in state("clients")}, before | {result["address"]})
            record("Super+Enter launch/focus", address=result["address"], pid=result["pid"])
            return result["address"]

        try:
            self.assertEqual(state("clients"), [], "private session must start without fixture clients")
            self.assertEqual(state("activeworkspace")["id"], 1)
            first = launch()

            # Minimal US key mapping for this literal shell command, independent
            # of production config. Greater-than requires real Shift.
            command = "printf headlessok > /tmp/headless-marker"
            codes = {"p": 25, "r": 19, "i": 23, "n": 49, "t": 20, "f": 33,
                     " ": 57, "h": 35, "e": 18, "a": 30, "d": 32, "l": 38,
                     "s": 31, "o": 24, "k": 37, "/": 53, "m": 50, "-": 12}
            # A new virtual keyboard sends its keymap/focus before its first key.
            # Give the real terminal a harmless modifier event first, as every
            # binding sequence already does with Super; do not insert text twice.
            tokens = ["+42", "-42"]
            for character in command:
                if character == ">":
                    tokens.extend(("+42", "+52", "-52", "-42"))
                else:
                    tokens.extend((f"+{codes[character]}", f"-{codes[character]}"))
            keys(*tokens, "+28", "-28")
            marker = Path("/tmp/headless-marker")
            wait_for(lambda: marker.exists() and marker.read_text() == "headlessok", "literal shell marker headlessok")
            self.assertEqual(active(), first)
            (artifacts / "typed-marker.txt").write_text(marker.read_text())
            record("typed shell command", command=command, marker=marker.read_text())

            self.assertFalse(client(first)["floating"])
            for expected in (True, False):
                keys("+125", "+57", "-57", "-125")
                wait_for(lambda: client(first)["floating"] is expected and active() == first,
                         f"Super+Space floating={expected} on intended client")
                record("Super+Space", address=first, floating=expected)

            self.assertEqual(client(first)["fullscreen"], 0)
            for expected in (2, 0):
                keys("+125", "+42", "+33", "-33", "-42", "-125")
                wait_for(lambda: client(first)["fullscreen"] == expected and active() == first,
                         f"Super+Shift+F fullscreen={expected} on intended client")
                record("Super+Shift+F", address=first, fullscreen=expected)

            for code, expected in ((3, 2), (2, 1)):
                keys("+125", f"+{code}", f"-{code}", "-125")
                wait_for(lambda: state("activeworkspace")["id"] == expected,
                         f"raw Super+{expected} workspace={expected}")
                record("raw workspace key", evdev=code, workspace=expected)
            wait_for(lambda: active() == first, "workspace 1 restores original client focus")

            second, third = launch(), launch()
            self.assertEqual(len(state("clients")), 3)
            start = active()
            keys("+125", "+36", "-36", "-125")
            forward = wait_for(lambda: active() if active() != start else None, "Super+J changes focus")
            self.assertIn(forward, {first, second, third})
            keys("+125", "+36", "-36", "-125")
            forward_twice = wait_for(lambda: active() if active() not in {start, forward} else None,
                                     "second Super+J visits the third distinct client")
            self.assertEqual({start, forward, forward_twice}, {first, second, third})
            keys("+125", "+37", "-37", "-125")
            wait_for(lambda: active() == forward, "Super+K reverses second Super+J")
            keys("+125", "+37", "-37", "-125")
            wait_for(lambda: active() == start, "second Super+K returns to initial client")
            record("three-window J/K inverse focus", addresses=[start, forward, forward_twice, forward, start])
            (artifacts / "binds-before-reload.json").write_text(hyprctl("-j", "binds"))

            remaining = {first, second, third} - {start}
            keys("+125", "+16", "-16", "-125")
            wait_for(lambda: {c["address"] for c in state("clients")} == remaining,
                     "Super+Q removes only the intended active client")
            record("Super+Q close", closed=start, remaining=sorted(remaining))

            self.assertEqual(hyprctl("reload").strip(), "ok")
            self.assertEqual(hyprctl("configerrors").strip(), "")
            (artifacts / "binds-after-reload.json").write_text(hyprctl("-j", "binds"))
            after_reload = launch()
            record("reload static launch", address=after_reload, configerrors="",
                   limitation="Dynamic J/K/O after reload are user-deferred and not reinitialized or asserted")

            # A coarse rendering check, not a pixel golden or font acceptance.
            for extension in ("png", "ppm"):
                subprocess.run(["grim", "-o", "TEST-1", "-t", extension,
                                str(artifacts / f"daily-output.{extension}")], check=True, timeout=10)
            png = (artifacts / "daily-output.png").read_bytes()
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", png[16:24]), (1280, 720))
            ppm = (artifacts / "daily-output.ppm").read_bytes()
            magic, dimensions, maximum, pixels = ppm.split(b"\n", 3)
            self.assertEqual((magic, dimensions, maximum), (b"P6", b"1280 720", b"255"))
            self.assertEqual(len(pixels), 1280 * 720 * 3)
            self.assertGreater(len(set(pixels[i:i + 3] for i in range(0, len(pixels), 3))), 1)
            self.assertTrue(any(pixels), "captured frame is entirely black")
            record("nonblank screenshot", dimensions=[1280, 720], png_bytes=len(png))
        finally:
            self._collect_final_diagnostics(artifacts, owned_clients,
                                            original_failure=sys.exc_info()[0] is not None)

    def _collect_final_diagnostics(self, artifacts, owned_clients, original_failure):
        errors = []

        def attempt(stage, operation):
            try:
                operation()
            except Exception as error:
                errors.append({"stage": stage, "type": type(error).__name__, "error": str(error)})

        for name in ("clients", "activewindow", "activeworkspace"):
            attempt(f"final-{name}", lambda name=name:
                    (artifacts / f"daily-final-{name}.json").write_text(hyprctl("-j", name)))
        attempt("final-screenshot", lambda: subprocess.run(
            ["grim", "-o", "TEST-1", str(artifacts / "daily-final.png")], check=True, timeout=10))
        attempt("marker-diagnostic", lambda:
                (artifacts / "marker-diagnostic.json").write_text(json.dumps({
                    "exists": Path("/tmp/headless-marker").exists(),
                    "contents": Path("/tmp/headless-marker").read_text()
                    if Path("/tmp/headless-marker").exists() else None})))

        def cleanup_owned_clients():
            # Test-owned application teardown only, after screenshots/evidence.
            # This isolated stack has observed shutdown instability; application
            # cleanup yields the verified normal path, with crashes fail-closed.
            closed = []
            for _ in range(len(owned_clients)):
                remaining = {c["address"] for c in state("clients")} & owned_clients
                if not remaining:
                    break
                intended = state("activewindow").get("address")
                self.assertIn(intended, remaining, "cleanup must close only a focused test-owned client")
                keys("+125", "+16", "-16", "-125")
                wait_for(lambda: all(c["address"] != intended for c in state("clients")),
                         "test-owned Ghostty cleanup")
                closed.append(intended)
            self.assertFalse({c["address"] for c in state("clients")} & owned_clients)
            (artifacts / "daily-client-cleanup.json").write_text(json.dumps({"closed": closed, "remaining_owned": []}))

        attempt("owned-client-cleanup", cleanup_owned_clients)
        attempt("diagnostic-error-record", lambda:
                (artifacts / "diagnostic-errors.json").write_text(json.dumps(errors, indent=2)))
        if errors and not original_failure:
            raise AssertionError(f"Final diagnostics or cleanup failed: {errors}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

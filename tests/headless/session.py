#!/usr/bin/env python3
"""Own only container children, private sockets and a disposable config copy."""
import glob
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import traceback

ARTIFACTS = Path("/artifacts")
children = []
logs = []


def command(args, env, timeout=5):
    return subprocess.check_output(args, env=env, text=True, stderr=subprocess.STDOUT, timeout=timeout)


def spawn(args, env, name):
    log = (ARTIFACTS / (name + ".log")).open("w")
    logs.append(log)
    child = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    children.append(child)
    return child


def wait_for(predicate, description, timeout=25):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        for child in children:
            if child.poll() is not None:
                raise RuntimeError(f"child PID {child.pid} exited {child.returncode} while waiting for {description}")
        try:
            result = predicate()
            if result:
                return result
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            last = error
        time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for {description}; last error: {last}")


def prepare(home):
    target = home / ".config/hypr"
    shutil.copytree("/source", target, ignore=shutil.ignore_patterns(
        ".git", ".worktrees", ".superpowers", "artifacts", "__pycache__"))
    original = target / "startup.lua"
    original.rename(target / "startup-production.lua")
    # Preserve the production startup registration and actual scripts; suppress
    # desktop services unrelated to the keybinding tests in this private copy.
    original.write_text('''local register = dofile(os.getenv("HOME") .. "/.config/hypr/startup-production.lua")
return function(command)
    local name
    if command:match("/ChangeLayout.sh init$") then name = "change-layout" end
    if command:match("/KeybindsLayoutInit.sh$") then name = "keybinds-layout" end
    if name then
        local log = os.getenv("HEADLESS_ARTIFACTS") .. "/startup-" .. name .. ".log"
        local done = os.getenv("HEADLESS_ARTIFACTS") .. "/startup-" .. name .. ".done"
        register("sh -c '" .. command .. " >" .. log .. " 2>&1; result=$?; printf %s $result >" .. done .. "; exit $result'")
    end
end
''')
    (target / "headless.lua").write_text('''dofile(os.getenv("HOME") .. "/.config/hypr/hyprland.lua")
hl.monitor({output="", mode="1280x720@60", position="auto", scale=1})
''')
    ghostty = home / ".config/ghostty"
    ghostty.mkdir()
    (ghostty / "config").write_text("command = /bin/bash --noprofile --norc\nfont-family = DejaVu Sans Mono\nfont-size = 14\n")
    # The notification daemon is outside this test's startup scope. Replace only
    # notification delivery, keeping the real startup scripts and hyprctl intact.
    fixture_bin = home / "test-bin"
    fixture_bin.mkdir()
    notify = fixture_bin / "notify-send"
    notify.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HEADLESS_ARTIFACTS/notifications.txt"\n')
    notify.chmod(0o755)
    return target / "headless.lua"


def main():
    ARTIFACTS.mkdir(exist_ok=True)
    status = 1
    with tempfile.TemporaryDirectory(prefix="ht-") as temporary:
        root = Path(temporary)
        home = root / "h"
        home.mkdir()
        runtime = root / "r"
        runtime.mkdir(mode=0o700)
        env = {key: value for key, value in os.environ.items() if key in ("PATH", "LANG", "HEADLESS_RENDER_NODE")}
        env.update(HOME=str(home), XDG_RUNTIME_DIR=str(runtime), XDG_CONFIG_HOME=str(home / ".config"),
                   XDG_SESSION_TYPE="wayland", XDG_CURRENT_DESKTOP="Hyprland", HEADLESS_ARTIFACTS=str(ARTIFACTS),
                   AQ_DRM_DEVICES=os.environ["HEADLESS_RENDER_NODE"], LIBSEAT_BACKEND="noop",
                   WLR_BACKENDS="headless", WLR_RENDERER="gles2",
                   WLR_RENDER_DRM_DEVICE=os.environ["HEADLESS_RENDER_NODE"])
        hyprland = None
        signature = None
        try:
            config = prepare(home)
            env["PATH"] = str(home / "test-bin") + ":" + env["PATH"]
            (ARTIFACTS / "packages.txt").write_text(Path("/image-packages.txt").read_text())
            spawn(["dbus-daemon", "--session", "--nofork", "--address=unix:path=" + str(runtime / "bus")], env, "dbus")
            wait_for(lambda: (runtime / "bus").is_socket(), "private D-Bus socket")
            env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=" + str(runtime / "bus")
            (ARTIFACTS / "bootstrap-source-sha256.txt").write_text(Path("/bootstrap-source-sha256.txt").read_text())
            (ARTIFACTS / "bootstrap-versions.txt").write_text(Path("/bootstrap-versions.txt").read_text())
            spawn(["tinywl"], env, "bootstrap")
            bootstrap = wait_for(lambda: next((p.name for p in runtime.glob("wayland-*") if p.is_socket()), None), "private wlroots GL socket")
            env["WAYLAND_DISPLAY"] = bootstrap
            globals_info = command(["wayland-info"], env)
            (ARTIFACTS / "bootstrap-protocols.txt").write_text(globals_info)
            import re
            for interface, version in {"wl_seat": 9, "xdg_wm_base": 6, "wl_compositor": 6,
                                       "wl_shm": 1, "zwp_linux_dmabuf_v1": 4}.items():
                match = re.search(r"interface: '" + interface + r"',\s+version:\s+(\d+)", globals_info)
                if not match or int(match.group(1)) < version:
                    raise RuntimeError(f"Bootstrap lacks {interface} v{version}; see bootstrap-protocols.txt")
            hyprland = spawn(["Hyprland", "--config", str(config)], env, "hyprland")
            # An initially empty private runtime has exactly this child's IPC.
            socket = wait_for(lambda: next(iter(glob.glob(str(runtime / "hypr/*/.socket.sock"))), None), "child Hyprland IPC")
            signature = Path(socket).parent.name
            env["HYPRLAND_INSTANCE_SIGNATURE"] = signature
            ctl = lambda *args: command(["hyprctl", "-i", signature, *args], env)
            wait_for(lambda: ctl("version").strip(), "child Hyprland readiness")
            instances = json.loads(command(["hyprctl", "-j", "instances"], env))
            if not any(item["instance"] == signature and item["pid"] == hyprland.pid for item in instances):
                raise RuntimeError("Private IPC signature does not match the child PID")
            ctl("output", "create", "headless", "TEST-1")
            ctl("eval", 'hl.monitor({output="TEST-1",mode="1280x720@60",position="0x0",scale=1})')
            wait_for(lambda: any(m["name"] == "TEST-1" for m in json.loads(ctl("-j", "monitors"))), "native TEST-1 output")
            for monitor in json.loads(ctl("-j", "monitors")):
                if monitor["name"] != "TEST-1":
                    ctl("output", "remove", monitor["name"])
            env["WAYLAND_DISPLAY"] = wait_for(lambda: next((p.name for p in runtime.glob("wayland-*") if p.is_socket() and p.name != bootstrap), None), "child Wayland display")
            required_startup = ("change-layout", "keybinds-layout")
            wait_for(lambda: all((ARTIFACTS / f"startup-{name}.done").is_file()
                     and (ARTIFACTS / f"startup-{name}.done").read_text().strip()
                     for name in required_startup), "real startup callbacks")
            startup_status = {name: int((ARTIFACTS / f"startup-{name}.done").read_text())
                              for name in required_startup}
            (ARTIFACTS / "startup-status.json").write_text(json.dumps(startup_status))
            if any(code != 0 for code in startup_status.values()):
                raise RuntimeError(f"Required startup callback failed: {startup_status}; see startup-*.log")
            (ARTIFACTS / "session.json").write_text(json.dumps({"hyprland_pid": hyprland.pid, "instance": signature,
                "wayland_display": env["WAYLAND_DISPLAY"], "runtime": str(runtime), "home": str(home)}, indent=2))
            test_file = Path(os.environ.get("HEADLESS_TEST_FILE", "tests/headless/test_runtime.py"))
            if test_file.is_absolute() or ".." in test_file.parts:
                raise ValueError("HEADLESS_TEST_FILE must be a repository-relative path")
            test = subprocess.run(["python3", str(home / ".config/hypr" / test_file)], env=env, timeout=100)
            status = test.returncode
            for name, args in {"monitors": ("-j", "monitors", "all"), "clients": ("-j", "clients"),
                               "devices": ("-j", "devices"), "version": ("version",), "systeminfo": ("systeminfo",),
                               "configerrors": ("configerrors",)}.items():
                (ARTIFACTS / (name + ".txt")).write_text(ctl(*args))
        except Exception:
            status = 1
            traceback.print_exc()
        finally:
            # Reap each consumer before stopping its renderer/D-Bus dependency.
            # A completed assertion suite must not hide a shutdown crash.
            forced_kills = []
            unexpected_exits = []
            for child in reversed(children):
                sent_term = False
                if child is hyprland and signature and child.poll() is None:
                    # Normal shutdown runs on the compositor event loop with its
                    # clients/dependencies alive. SIGTERM remains bounded fallback.
                    try:
                        result = subprocess.run(["hyprctl", "-i", signature, "eval", "hl.dispatch(hl.dsp.exit())"],
                                                env=env, text=True, stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, timeout=5)
                        # Retain both control transport and reaped process status.
                        # A successful request alone does not prove clean shutdown.
                        (ARTIFACTS / "teardown-exit.json").write_text(json.dumps({
                            "hyprctl_returncode": result.returncode, "output": result.stdout}))
                        child.wait(timeout=5)
                    except (OSError, subprocess.SubprocessError) as error:
                        (ARTIFACTS / "teardown-exit-error.txt").write_text(str(error))
                if child.poll() is None:
                    sent_term = True
                    os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    forced_kills.append(child.pid)
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
                if child.returncode != 0 and not (sent_term and child.returncode == -signal.SIGTERM):
                    unexpected_exits.append({"pid": child.pid, "returncode": child.returncode})
            # Copy diagnostics after teardown too: a shutdown crash report may
            # not exist until its process has actually exited.
            for pattern in ("r/hypr/*/hyprland.log", "h/.cache/hyprland/*.txt"):
                for diagnostic in root.glob(pattern):
                    shutil.copy2(diagnostic, ARTIFACTS / ("private-" + diagnostic.name))
            (ARTIFACTS / "cleanup.json").write_text(json.dumps({"children": [
                {"pid": child.pid, "returncode": child.returncode} for child in children],
                "all_reaped": all(child.poll() is not None for child in children),
                "forced_kills": forced_kills, "unexpected_exits": unexpected_exits}))
            if forced_kills or unexpected_exits:
                print(f"FAIL: unclean session teardown: forced_kills={forced_kills}, unexpected_exits={unexpected_exits}", flush=True)
                status = 1
            for log in logs:
                log.close()
    return status


def interrupted(signum, frame):
    raise RuntimeError(f"Interrupted by signal {signum}")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    raise SystemExit(main())

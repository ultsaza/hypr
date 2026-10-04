# Headless Runtime Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exercise the real Lua configuration and everyday keybindings in an isolated, headless Hyprland session, replacing the old parser-only test entry point.

**Architecture:** Run Hyprland 0.56.2 and actual Ghostty inside Docker. A private headless tinywl (wlroots 0.18.2) supplies the Wayland/DRM rendering bootstrap, while assertions target Hyprland's own headless output; pass only a DRM render node, not display-control or input devices. Drive real key events and verify IPC state, terminal side effects, and a captured frame.

**Tech Stack:** Docker, Ubuntu 24.04, Hyprland 0.56.2, wlroots 0.18.2/tinywl, Ghostty, Python standard library, Wayland virtual-keyboard protocol.

**Initial rendering investigation:** Disposable runs showed Weston 13 could render on the AMD render node, but advertised `wl_compositor` version 5 while Aquamarine required version 6. Official Sway 1.9 `sway/server.c` advertises version 6, so it was tried next without adding host device access. Weston 14–16 source also advertised version 5, so upgrading a released Weston would not fix this mismatch.

**Rendering decision update:** Sway 1.9 then rejected Aquamarine's xdg-shell v6 request (it exposes v2); Sway 1.10–1.12 expose only v5. Inspected Aquamarine's full required matrix: compositor 6, seat 9, xdg-shell 6, linux-dmabuf 4, shm 1. wlroots 0.18.2 implements these versions, so build its tinywl example with compositor/xdg-shell API arguments set to 6 instead of its conservative 5/3 defaults. This selects implemented library capabilities, not fake advertised versions. Build a compatible Wayland library in the image; do not modify Hyprland or Aquamarine. Probe all globals together before rerunning Hyprland.

## Global Constraints

- Work only in `/home/ultsaza/.config/hypr/.worktrees/v0.55+` on branch `v0.55+`.
- Do not commit, push, change the live configuration, or operate the host compositor.
- Do not mount host HOME, runtime/Wayland/D-Bus sockets, input devices, DRM card nodes, or the Docker socket. Do not use privileged containers, host PID/network namespaces, or install packages on the host.
- Docker may use only an explicitly checked DRM render node; run test processes unprivileged with a private HOME, runtime directory and D-Bus session. Repository input is read-only and copied to disposable storage; artifacts are the sole writable host mount.
- Keep production Lua and scripts unchanged. Test adapters may filter unrelated startup services, but must preserve the actual registration/execution of `ChangeLayout.sh init` and `KeybindsLayoutInit.sh`.
- Test keybindings with keyboard events, not by dispatching the action under test. Bindings and expected values come from independent literal test cases.
- Missing dependencies or an unusable rendering environment must fail clearly, never report a skipped suite as success.
- Pin Hyprland to 0.56.2 and document other image/version inputs and limitations. Do not imply CPU-only or GPU-driver-independent support.
- README and new documentation are English. Keep README concise and put detailed coverage/limitations in `tests/README.md`.
- The old `tests/test_native_config.py` and `tests/test_config_guards.py` may be removed only after the headless suite is operational. Document any coverage not retained.
- Do not silently fix existing desktop behavior or user-deferred defects to make tests green.

### Task 1: Isolated rendering and input foundation

**Files:**
- Create: `tests/headless/Dockerfile`, `tests/headless/run.sh`, `tests/headless/session.py`.
- Create as needed: a small raw-keycode Wayland test client and its protocol/build inputs under `tests/headless/`.
- Create: `tests/headless/test_runtime.py` with an initial smoke scenario.
- Modify: `.gitignore` only for generated test artifacts.

**Interfaces:**
- Host entry point: `bash tests/headless/run.sh` builds the image, selects a verified render node, starts a bounded disposable container, and preserves artifacts under a unique ignored directory.
- Container entry point: `session.py` prepares a disposable HOME and private tinywl/Hyprland/D-Bus session, selects the exact child instance, creates `TEST-1`, exports only that instance/socket to test subprocesses, runs `test_runtime.py`, saves diagnostics, and terminates only its own children.
- Test process receives `HOME`, `XDG_RUNTIME_DIR`, `HYPRLAND_INSTANCE_SIGNATURE`, `WAYLAND_DISPLAY`, and an artifact directory; all identify the isolated session.
- Input helper supports raw evdev keycodes and modifier press/release sequences with a real US XKB keymap (`ctrl:nocaps` when applicable). An existing tool can replace custom code only if it demonstrably preserves code-based bindings.

- [x] **Step 1: Write the smoke assertions first.** Verify one named output exists and is enabled at scale 1; verify `configerrors` is empty. The meaningful failure is no usable headless session, not a skipped test.

```python
monitors = json.loads(hyprctl("-j", "monitors"))
monitor = next(item for item in monitors if item["name"] == "TEST-1")
assert monitor["scale"] == 1.0
assert hyprctl("configerrors").strip() == ""
```

- [x] **Step 2: Run the smoke before the environment exists and record the expected failure.** Do not call host `hyprctl`; exercise only the isolated runner or a disposable container.
- [x] **Step 3: Build the smallest viable pinned container.** Investigate packages and rendering there, using only the render node. tinywl is private and headless; remove/disable the temporary Hyprland Wayland output after its own headless output is available. If this topology cannot work without broad host access, report evidence before widening authority.
- [x] **Step 4: Add bounded lifecycle handling and diagnostics.** Check command failures, use deadline-based readiness, propagate test failures, retain logs/JSON/screenshots when possible, and clean up on normal exit and interruption.
- [x] **Step 5: Run the smoke successfully and demonstrate a real virtual keyboard event reaches the test compositor.** Record image packages, actual output backend, renderer and cleanup evidence. Test a missing-render-node preflight without contacting host IPC.

### Task 2: Everyday behavior, honest failure detection, and documentation

**Files:**
- Modify: `tests/headless/test_runtime.py`, session adapter only as required.
- Create: `tests/README.md`.
- Modify: `README.md`.
- Delete after successful replacement: `tests/test_native_config.py`, `tests/test_config_guards.py`.

**Interfaces:**
- Reuse Task 1's isolated session and raw-key input helper; never recreate production keybindings in the test adapter.
- `run.sh` returns nonzero for failed assertions or setup, and prints the artifact location.

- [x] **Step 1: Write literal scenarios and expected results before expanding implementation.** Catch a removed Super+Enter binding, broken terminal command, lost focus, wrong float/fullscreen action, wrong code-based workspace binding, and broken close action.

```text
Super+Enter -> new Ghostty client, mapped and focused
Type a shell command -> marker file contains the expected literal
Super+Space twice -> floating true then false
Super+Shift+F twice -> fullscreen then restored
Super+2 -> active workspace 2 (raw code binding)
Super+1 -> active workspace 1
Open three Ghostty windows, Super+J / Super+K -> focus changes and returns (three windows distinguish inverse directions)
Super+Q -> the intended client disappears
Reload -> no config errors; Super+Enter still launches Ghostty
```

- [x] **Step 2: Run the real scenarios and diagnose failures without changing production behavior.** Use client addresses and bounded state predicates. Separate known existing defects from test-harness errors.
- [x] **Step 3: Preserve a real nonblank screenshot of the headless output.** Assert successful capture and dimensions; do not call this visual/font correctness or compare renderer-sensitive pixels as an exact golden image.
- [x] **Step 4: Prove the suite can fail.** In a disposable configuration copy only, remove the Super+Enter binding or replace the terminal command with a nonexistent command; the normal launch scenario must fail and the host runner must return nonzero. Restore the unmodified input and rerun successfully.
- [x] **Step 5: Replace the old entry point and document the contract.** Delete the two legacy scripts after passing headless verification, describe removed preset/update-guard coverage, prerequisites, exact command, isolation, startup exclusions, artifacts, and remaining real-machine checks. Keep the top-level README short.
- [x] **Step 6: Final verification.** Run `bash tests/headless/run.sh`, failure-injection verification, `git diff --check`, inspect the final diff, and confirm no test container/process remains. Leave changes uncommitted.

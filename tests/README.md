# Isolated runtime tests

Run from the repository root:

```sh
bash tests/headless/run.sh
```

The command builds the image, starts a disposable private session, and returns
nonzero on setup or assertion failure. It prints a unique ignored directory under
`tests/headless/artifacts/`. Missing rendering prerequisites fail; they do not skip
the suite. Do not use unittest discovery as the entry point: these tests require
the private session environment supplied by the runner.

## Prerequisites and image inputs

- Linux amd64, Bash, GNU timeout/coreutils, tar, and a running local Docker daemon
  that the caller may use. Remote Docker cannot access these local bind paths.
- A compatible GPU/kernel driver and a readable/writable DRM render node.
  `/dev/dri/renderD128` is the default; override with
  `HEADLESS_RENDER_NODE=/dev/dri/renderD129 bash tests/headless/run.sh` when needed.
  Only paths matching `/dev/dri/renderD[0-9]+` that are character devices and
  accessible to the caller are accepted. No DRM card or input device is required.
- Network access during image build for the pinned public sources and signed
  Ubuntu/PPA repositories. The running test container has networking disabled.
- Space for the image (about 1 GB in the initial verified environment), build
  cache and retained screenshots/logs. Build and runtime deadlines are 600 and
  180 seconds; individual input, IPC and assertion waits are also bounded.

The Dockerfile pins Ubuntu 24.04 by digest, Hyprland `0.56.2-1ppa2`, Aquamarine
`0.15.1-1ppa1`, Ghostty `1.2.3-0~ppa1` by archive SHA256, Wayland 1.23.1 and
wlroots 0.18.2 by commit/archive checksums. Tinywl is built from that wlroots
source, exposing supported compositor/xdg-shell version 6 APIs for Hyprland's
bootstrap. Other signed distribution packages are recorded in `packages.txt`
but are not frozen repository snapshots. Each run creates and uses an immutable
image ID in `image-id.txt`; it does not depend on a shared mutable image tag.

The initial successful renderer was Mesa/radeonsi on AMD Rembrandt. This suite is
driver dependent: it is not CPU-only, GPU-independent or evidence of support for
all Linux/GPU combinations. Source-built library versions are recorded separately
in `bootstrap-versions.txt`; distribution package metadata alone omits them.

## Isolation and startup scope

The caller's UID/GID runs the test processes with capabilities dropped,
no-new-privileges and only the checked render node's group. Docker uses private
namespaces, no privileged mode and no host PID/network namespace. There are no
host HOME, runtime, Wayland/D-Bus socket, input-device, card-node or Docker-socket
mounts. Repository input is read-only and copied into disposable container
storage; artifacts are the only writable host mount. Avoid editing repository
input concurrently with a run, because a bind mount is not an immutable snapshot.

The session owns its private HOME, runtime, D-Bus, tinywl bootstrap and child
Hyprland. It verifies the child PID/instance signature and points all test IPC and
Wayland input at that child. Tinywl supplies the bootstrap protocols/renderer;
Hyprland creates its native `TEST-1` output at 1280x720, scale 1. Tests require it
to be the sole enabled output. Cleanup signals/reaps only recorded children and
removes the test container, including on interruption.

The disposable startup adapter preserves original `startup.lua` registration and
executes the actual `ChangeLayout.sh init` and `KeybindsLayoutInit.sh`. Both real
exit statuses must be zero before tests run. Other startup applications/services
are excluded, including bars, launchers, wallpaper, tray, portal/desktop services
and drop-down terminals. Only `notify-send` delivery is replaced in private PATH
by a narrow logging fixture because the notification daemon is excluded. Hyprctl,
the init scripts, keybindings and their actions remain real.

Ghostty is the actual installed application. Its private minimal fixture selects
`/bin/bash --noprofile --norc`, DejaVu Sans Mono and size 14. Personal shell, font,
theme and IME configurations are outside the test. Production repository
Lua/scripts remain unchanged; the adapter operates only on disposable copies.
Expected Hyprland warning overlays report missing `hyprland-qtutils` and direct
`Hyprland` launch rather than `start-hyprland`. This deliberate debug environment
does not hide those warnings or claim a complete warning-free desktop.

## Tested behavior

The suite has four foundation assertions and one ordered daily-operation
test. The daily test stops on a failed prerequisite and records each completed
scenario with real client addresses. State predicates use deadlines rather than
assuming window mapping or state transitions have completed.

| Input or control | Expected observation |
| --- | --- |
| Settings helper and compositor EDITOR | Both select `nvim` as the default editor |
| Super+Enter | One new mapped Ghostty client, focused by its address |
| Literal shell typing and Enter | `/tmp/headless-marker` contains exactly `headlessok` |
| Super+Space twice | Intended client floating true, then false |
| Super+Shift+F twice | Intended client fullscreen 2, then 0 |
| Raw Super+2, Super+1 | Active workspace 2, then 1; original client focus restored |
| Three Ghostty clients, J/J/K/K with Super | Three distinct focus addresses, followed by the inverse sequence |
| Super+Q | Intended client disappears; the other clients remain |
| Explicit config reload, Super+Enter | No config errors and static terminal binding launches/focuses Ghostty |
| Grim capture of TEST-1 | Successful 1280x720 PNG/PPM; varied, nonblack PPM pixels |

The editor check verifies selection and environment export, not Neovim's UI or
personal plugins.

Input uses raw evdev events through Wayland's real virtual keyboard protocol and
a real US XKB keymap with `ctrl:nocaps`. Workspace events use physical keycodes
(evdev 3/2, XKB 11/10), independent of configuration source. No dispatcher stands
in for any tested keyboard action; `reload` is an explicit configuration control.
The input helper creates a fresh keyboard on each call. The literal typing
sequence begins with harmless Shift press/release events to allow its keymap/focus
handoff, matching the modifier-first shortcut sequences. An initial diagnostic
run without this prefix lost the first typed `p`; failure screenshots exposed it.
This uses the helper's existing protocol roundtrips/event pacing, without an
additional arbitrary sleep or retrying the command. The complete literal marker
and address/state assertions still fail when delivery or the action is wrong.

Dynamic J/K/O bindings currently disappear on reload, a known user-deferred
behavior. J/K are tested before reload; the harness does not rerun init scripts
afterward. Only static launch and config errors are checked after reload.
Before/after binding dumps document the boundary. Do not interpret a passing run
as post-reload cycling coverage.

Shutdown instability was observed on this isolated pinned stack: SIGSEGV occurred
with open Ghostty clients under SIGTERM and native Lua graceful exit, and also in
a failed-launch negative run without clients. Dependency ordering alone did not
remove it; no root cause or general desktop defect is established. Closing only
recorded, focused test-owned Ghostty clients with real Super+Q after preserving
screenshots/observations yields the verified normal path. This is application
cleanup, not a fix or acceptance test for exiting a desktop in other states.
The session then requests private compositor exit, waits/reaps it before stopping
its dependencies, and uses bounded signal fallback. Any unexpected child exit or
forced kill still makes the host run fail; `cleanup.json` records that evidence.
The native Lua exit control is `hyprctl eval 'hl.dispatch(hl.dsp.exit())'` against
the exact child signature. Both its result and the reaped compositor status are
retained; a successful control request alone does not prove clean shutdown.

## Artifacts and failure proof

`session.log` contains unittest results and scenario progress;
`daily-scenarios.json` contains completed action/state evidence. `typed-marker.txt`
preserves the shell result. `daily-output.png` and `.ppm` preserve the successful
frame, and `daily-final.png` is attempted even after a failed daily assertion.
Final daily IPC, screenshot, marker and owned-client cleanup attempts run
independently; `diagnostic-errors.json` records each collection/cleanup error.
An existing scenario failure is preserved. If scenarios otherwise pass, a final
diagnostic/cleanup error fails the test. Final daily client/focus/workspace JSON
and marker diagnostics help locate a failure. General artifacts include build
logs, version/systeminfo, monitors,
devices/clients/configerrors, bootstrap logs/protocols/source hashes, Hyprland
logs/crash reports, startup command logs/exit markers/status, notification calls,
private session identifiers, image/container inspections, `daily-client-cleanup.json`,
`teardown-exit.json` and `cleanup.json`. Crash diagnostics are collected after
teardown as well; a crash in upstream cleanup may lack a crash report because
that path restores default signal handlers.
`container-final.json` records the actual container exit status on completed runs.

To verify the launch test detects a regression, create a disposable repository
snapshot under the ignored artifacts directory (exclude Git metadata, worktrees,
`.superpowers`, artifacts and caches), remove only its Super+Enter registration
in `configs/Keybinds.lua`, and run that snapshot's normal
`bash tests/headless/run.sh`. The normal launch/focus assertion must time out and
the host runner must return nonzero; require that status explicitly. Restore the
snapshot's original binding and rerun, then run the unmodified main worktree.
Never perform this mutation in production source or the live configuration.

## Replaced coverage and real-machine checks

The old `test_native_config.py` and `test_config_guards.py` were removed after
the real headless replacement passed. The loaded production entry point and
runtime config errors are covered here. Enumerating every selectable animation
and monitor preset with `--verify-config`, and sandbox sentinel checks for retired
`UserConfigsSwitcher.sh`, `KooLsDotsUpdate.sh` and `update_WindowRules.sh`, are no
longer covered. This suite is not a complete replacement for those distinct checks.

The screenshot assertion is a coarse capture/rendering check, not a pixel golden,
layout/font acceptance or proof of finished animations. Inspect the retained image
when diagnosing failures. Real-machine acceptance remains necessary for physical
displays/mixed scaling/hotplug, keyboards and pointing devices, Japanese IME,
personal shells/fonts/themes, Waybar and startup services, wallpaper, portals,
clipboard/audio/network, lock/idle/power, screen sharing, hardware acceleration
and extended session stability. None of those flows is claimed by this suite.

# Lua-only branch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Keep only the native Lua Hyprland configuration on a separate local branch, without switching the live desktop.

**Architecture:** Branch `v0.55+` starts after the 100% monitor-scale commit on `main`. Remove superseded Hyprland config files, retain companion applications' own formats, and preserve effective Lua settings and scripts. Keep history available in Git rather than carrying rollback copies in the branch tree.

**Tech Stack:** Git worktrees, Hyprland 0.56.2 native Lua, Bash, Python unittest.

## Global Constraints

- Keep the running desktop and `main` checkout unchanged during cleanup.
- Preserve the pre-existing uncommitted `monitors.conf` in the live checkout.
- Retain 100% scaling, resolution, rotation, and adjacent monitor positions.
- Do not fix previously deferred keybinding/Rainbow Borders issues.
- Keep `application-style.conf`, `hypridle.conf`, `hyprlock.conf`, `hyprlock-1080p.conf`, `hyprlock-2k.conf`, and `xdph.conf`: these belong to other applications.
- Keep all native Lua modules, presets, and active helper scripts.
- Commit locally. Do not push, merge into `main`, or switch the live checkout.

---

### Task 1: Remove superseded configuration and document the branch

**Files:**
- Remove: `hyprland.conf`, `monitors.conf`, `workspaces.conf`, `configs/*.conf`, `UserConfigs/*.conf`, `UserConfigs/*.disable`, `animations/*.conf`, `Monitor_Profiles/*.conf`, `scripts/keybinds_parser.py`.
- Modify: `scripts/KooLsDotsUpdate.sh`, `scripts/update_WindowRules.sh`, `scripts/UserConfigsSwitcher.sh` (retain their protective notification/no-op entry points, remove legacy replacement bodies).
- Modify: Lua/header/help comments pointing users to removed files, `UserConfigs/00-Readme`, `Monitor_Profiles/README`, `docs/lua-migration.md`.
- Create: `README.md`, `tests/test_config_guards.py`, `tests/test_native_config.py`.

**Interfaces:**
- Consumes: native `hyprland.lua` and modules at `b624a7c`; shell guard entry points used by existing desktop tools.
- Produces: a native-only repository tree with unchanged active configuration and safe no-op legacy entry points.

- [x] Establish a clean baseline using the real parser in a temporary runtime directory:

```sh
verification_dir=$(mktemp -d /tmp/hypr-lua-only-verify.XXXXXX)
env -u HYPRLAND_INSTANCE_SIGNATURE -u WAYLAND_DISPLAY XDG_RUNTIME_DIR="$verification_dir" \
  Hyprland --verify-config --config "$PWD/hyprland.lua"
```

- [x] Test the guard entry points in a temporary home with only disposable UserConfigs data, no running desktop and a stub notification command. Assert success and unchanged data even without `hyprland.lua`; the current switcher should fail this test by moving UserConfigs.

```sh
python3 -B -m unittest discover -s tests -v
```

- [x] Remove only the audited legacy paths above using `apply_patch`. Confirm every `.conf` that remains belongs to the six-file companion-app allowlist. Remove the unreferenced legacy key parser, but keep `keybinds_live.py`.
- [x] Simplify guard scripts to their existing notification/print plus `exit 0`, with no fallback to directory replacement. Run the behavior tests again; all must pass.
- [x] Update editing guidance to `.lua` and add README instructions for the branch, companion configs, external dependencies, verification, and recovery through Git history. Keep migration notes as historical evidence with an explicit branch update.
- [x] Validate the branch's entry point and every animation/monitor preset with the installed Hyprland parser. Trace module loads to confirm they use the worktree, not the live config. Run `bash -n` for tracked shell scripts and check Python syntax in memory. For the unchanged self-contained `scripts/RofiEmoji.sh`, validate only the executable prefix before its `# # DATA # #` marker; the suffix is emoji data, not Bash.
- [x] Compare executable Lua lines before/after (comments excluded), review removed-file references, run `git diff --check`, and obtain an independent read-only review.
- [x] Commit cleanup on `v0.55+`. Verify branch separation, clean worktree, unchanged live `monitors.conf` hash and current monitor state. Do not push.

## Verification record

- Baseline and cleaned entry point: `config ok` with installed Hyprland 0.56.2.
- Guard regression reproduced before cleanup, then all 5 tests passed (including 18 selectable presets plus the entry point).
- All 42 Lua files retain identical executable lines; comments and blank lines are the only Lua changes.
- 68 shell scripts/wrappers passed syntax checks (emoji data excluded as above); retained Python helpers passed syntax checks.
- Native open trace confirms all 23 loaded Lua files came from the isolated worktree.
- Removed 43 legacy files; retained the 6 companion `.conf` files unchanged.
- Independent read-only review: no critical, important, or actionable minor findings.
- Live `main` retains the pre-existing `monitors.conf` change; its hash was unchanged, both live monitors remained at scale 1, and live config errors were empty.

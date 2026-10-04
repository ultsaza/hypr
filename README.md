# Hyprland Configuration

Personal native Lua configuration on the `v0.55+` branch, tested with Hyprland **0.56.2**. Lua support is required; compatibility with 0.55 is not guaranteed.

## Layout

- `hyprland.lua`: entry point.
- `configs/`, `UserConfigs/`: defaults and personal overrides.
- `monitors.lua`, `workspaces.lua`: display and workspace settings.
- `animations/`, `Monitor_Profiles/`: selectable presets.
- `scripts/`, `UserScripts/`, `tools/`: helpers and companion tooling.

Edit `.lua` files for Hyprland settings. The remaining `.conf` files belong to Hypridle, Hyprlock, the desktop portal, and Qt styling. Legacy Hyprland settings are available in Git history.

## Validation

With local Docker and a compatible accessible DRM render node, run from the repository root:

```sh
bash tests/headless/run.sh
```

This starts an isolated Hyprland 0.56.2 session and tests real Ghostty and keyboard operations. Failures return nonzero; logs and screenshots are retained. See [test coverage and prerequisites](tests/README.md).

This is not a complete desktop installer; external apps and settings are required. Review upstream changes before applying them. See the [migration notes](docs/lua-migration.md) for details.

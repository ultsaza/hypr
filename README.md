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

With Hyprland installed, run from the repository root:

```sh
python3 -B -m unittest discover -s tests -v
```

This checks the Lua configuration, presets, and update guards without starting a desktop session.

This is not a complete desktop installer; external apps and settings are required. Review upstream changes before applying them. See the [migration notes](docs/lua-migration.md) for details.

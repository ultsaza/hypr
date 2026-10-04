# Personal Hyprland configuration — native Lua

`v0.55+` は、Hyprland本体の設定をLuaに統一したブランチです。
検証対象は **Hyprland 0.56.2**。ブランチ名は0.55系でのLua動作保証を意味しません。

通常の起点は `hyprland.lua`。`configs/` の既定値を読み込み、`UserConfigs/` で個人設定を追加・上書きします。編集先は `.lua` です。

## 構成

| パス | 用途 |
| --- | --- |
| `hyprland.lua`, `variables.lua`, `startup.lua` | 読み込み順、共通変数、起動時処理 |
| `configs/`, `UserConfigs/` | Lua設定の既定値と個人設定 |
| `monitors.lua`, `workspaces.lua` | 画面配置・倍率とワークスペース |
| `animations/`, `Monitor_Profiles/` | メニューから選択するLuaプリセット |
| `wallust/wallust-hyprland.lua` | Wallust配色 |
| `scripts/`, `UserScripts/` | キーバインドやメニューから呼ぶヘルパー |
| `tools/` | Lua対応の周辺ツール用ラッパーと再構築定義 |

モニターは両方100%。HDMI-A-1は3840×2160・位置3000×0、DP-2は1920×1080・縦向き・位置1920×0です。別の機器では `monitors.lua` を調整してください。

次の `.conf` は旧Hyprland設定ではなく、別アプリの現役設定なので残しています。

- `hypridle.conf`: アイドル処理
- `hyprlock.conf`, `hyprlock-1080p.conf`, `hyprlock-2k.conf`: ロック画面
- `xdph.conf`: 画面共有ポータル
- `application-style.conf`: Hyprland Qtアプリのスタイル

## 検証

リポジトリのルートで実行します。Luaを実際に評価しますが、自動起動処理は `hyprland.start` コールバックとして登録されるため、以下ではデスクトップアプリを起動しません。

```sh
verification_dir=$(mktemp -d /tmp/hypr-config-verify.XXXXXX)
env -u HYPRLAND_INSTANCE_SIGNATURE -u WAYLAND_DISPLAY XDG_RUNTIME_DIR="$verification_dir" \
  Hyprland --verify-config --config "$PWD/hyprland.lua"
python3 -B -m unittest discover -s tests -v
```

## 利用範囲・履歴

- このリポジトリは個人用設定です。Waybar、Wallustテンプレート、Rofi、AGS、フォント等の外部設定・依存アプリはすべてを同梱していません。周辺ツールの導入状況は [移行記録](docs/lua-migration.md) を参照してください。単独クローンだけで同じデスクトップが完成する構成ではありません。
- 旧Hyprlandの `.conf`、無効化済みオーバーレイ、旧キー解析コードはブランチのファイル一覧から除去しました。以前の内容は `b624a7c` およびそれ以前のGit履歴から参照・復元できます。履歴は書き換えていません。
- KooL更新・旧設定復元用の入口は、通知のみの保護処理として残しています。上流更新は差分を確認して必要な変更だけ取り込みます。
- 今回は別worktreeで整理しただけで、稼働中の設定フォルダーは `main` のままです。未検証の一括コピーや設定フォルダーの全置換は行わないでください。
- 以前から保留しているキー操作の課題（再読込後のJ/K/O消失、Tabの複数動作、Rainbow Borders等）は今回変更していません。

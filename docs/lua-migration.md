# Hyprland Lua設定への移行

状態: 2026-09-29に配置・再ログイン済み。ネイティブLuaで稼働し、設定エラーなし。基本設定・画面配置・アニメーション・キー登録を実セッションで比較済み。GhosttyのSuper+Enter起動はユーザー確認済み。テーマ切替・モニター設定GUIなどの全操作の実機確認は未完了。

## 合意済み

- Hyprland本体の設定を、公式Lua設定ガイドに従って移行する。
- 現在の見た目・キーバインド・自動起動・テーマ切替などの動作をできる限り維持し、Lua対応に必要な変更を行う。ユーザーが2026-09-28のQ1で選択した。
- 準備と検証が済んだら、この作業中にユーザーが再ログインし、Lua設定での実動作を確認する。ユーザーがQ2で選択した。
- 現在の個人設定を維持し、KooLの上流更新は差分を確認して取り込む。既存の更新ボタンからの全置換を防止する。ユーザーがQ3で選択した。[判断の記録](adr/0001-personal-config-updates.md)

## 移行前の状態

- インストール済みパッケージは `0.56.2-1ppa2`。実行中もHyprland `0.56.2`（コミット `efb5099`）。
- 既存セッションの `hyprctl configerrors` は空。設定プロバイダーは `hyprlang`、登録済みキーバインドは161件。
- Git履歴は設定ディレクトリの外に保存している。
- 調査開始時の未コミット変更は `monitors.conf`。現在の画面配置を移行元として保持する。
- Luaモードでは `hyprctl keyword` が使えず、`hyprctl dispatch` もLuaの式を受け取る。設定を操作する既存スクリプトも移行対象となる。
- 現在の `nwg-displays` は0.3.22で `.conf` を生成する。公式0.4.3でLua出力が導入され、0.4.4で追加修正されている。
- 起動は `start-hyprland` 経由で、明示的な設定ファイル指定はない。設定形式は起動時に決まるため、切替には再ログインが必要。

## 移行対象

| 対象 | 必要な対応 |
| --- | --- |
| 設定本体と分割設定 | 既定設定とユーザー設定の適用順を維持し、現在の値・キーバインド・ルールをLuaへ移す |
| アニメーションと画面プロファイル | 現在値に加えて、選択メニューから利用するプリセットとコピー先を対応させる |
| Wallust | `~/.config/wallust` の配色テンプレートと生成先、テーマ切替の参照先を対応させる |
| モニター設定GUI | nwg-displaysのLua対応版を用意し、現在の画面配置・拡大率・回転・ワークスペース設定を引き継ぐ |
| 設定を操作するスクリプト | キー一覧、設定メニュー、レイアウト切替、ぼかし、ゲームモード、入力機器、動画壁紙、自動起動などの読み書き・IPC呼び出しを対応させる |
| 更新操作 | KooLの更新ボタンによる設定フォルダー全置換を防ぎ、差分確認を経て取り込む運用を案内する |

Hypridle・Hyprlock・デスクトップポータルなど、別ツールの設定はそれぞれの対応形式を維持する。

## 検証・切替案

1. 未コミットのモニター変更と、Git管理外の関連設定・使用ツールの版を含む復帰用バックアップを用意する。
2. 作業用の場所でLua設定と関連スクリプトを準備する。上流のLua実装は参照し、現在の操作・表示との対応を確認する。
3. Luaのトップレベル処理に自動起動などの副作用がないことを確認してから、Hyprland 0.56.2の `--verify-config` で検証する。このコマンドはLuaを実際に評価するため、単なる構文検査として扱わない。
4. 設定値・キーバインド・画面配置・アニメーションを移行前と比較し、生成処理とスクリプトの動作を検証する。
5. 設定を配置し、ユーザーが再ログインする。Luaプロバイダーでの起動と設定エラーの有無を確認する。
6. キー操作、テーマとアニメーションの切替、モニター設定GUI、起動アプリなどを実際に確認する。問題があれば退避した設定・関連ファイルへ戻せるようにする。

## 実装・検証記録

ユーザーの「その方針で進めて」により、上記対象の変更を承認済み。

- 設定はネイティブLuaに変換。通常の起点は `hyprland.lua`、共通変数は `variables.lua`、自動起動は `startup.lua` の `hyprland.start` コールバック。実行時に旧設定を解釈する互換パーサーは使わない。
- 起動順序・ユーザー設定の上書き順を維持。既存 `.conf` は復帰用に保持するが、移行後に編集するのは `.lua`。Hypridle/Hyprlockの `.conf` は別ツール用として継続使用。
- 実際のHyprland Luaパーサーから取得した明示設定85項目は、稼働中の旧セッションと一致。キー・修飾キー・主要フラグ・説明160件も対応確認済み。旧セッション161件中、存在しない `XF86AudioPlayPause` の1件を除外し、有効な `XF86AudioPlay` は維持。
- アニメーション17種とモニタープロファイル1種、WallustのLuaテンプレート出力を実パーサーで検証。変更したシェルスクリプトは `bash -n` で検証。
- 切替スクリプトの実際のLua評価コード7件、色・機器設定とdispatcher生成7種を実パーサーで検証。設定配置・復帰処理は一時ディレクトリで、変更競合の拒否・ハッシュ一致・更新後の内容を保存して戻せることを確認。
- `SUPER+J/K/O` は従来どおり起動時・レイアウト切替時に追加される。移行直前のセッションでは設定リロード後のため登録されていない。起動後はこの追加分を区別して確認する。
- `workspaceopt allfloat` と旧 `splitratio` dispatcherは0.56.2ですでに無効だった。意図せず機能を復活させず、該当キーは明示的なno-opとして記録した。
- 無効な正規表現2件、区切り不足で意図したアプリに一致しなかったCodium/Heroic/Steamのpopupルール3件は無効のまま保持。
- 現在未選択のプリセット3種の `borderangle` speedはLuaの上限に合わせ180→100。未使用の範囲外ベジェ曲線 `nice` は登録しない。現在選択中のEND-4系アニメーションの値は変更していない。
- 更新ボタンと旧WindowRules更新処理からの一括上書きを無効化。`UserConfigsSwitcher.sh` もLua設定一式を移動・破棄しない保護を追加。

### 周辺ツールとGit管理外の設定

- Waybar: 上流コミット `8ebc788e802b1bf0d96b53e4b3815a9cee8a67c9`（表示バージョン0.15.0）をNixでユーザー領域にビルド。`~/.local/bin/waybar` → `~/.local/share/waybar-hyprlua/bin/waybar`。元の `/usr/bin/waybar` は残す。再構築定義は `tools/waybar-hyprlua.nix`。このデスクトップの音声可視化は従来の外部cavaを維持する。
- nwg-displays: 公式0.4.4 (`fd79522cb91ef2ba080ba51838c0f307e1d4fb83`) を `~/.local/share/nwg-displays-0.4.4` に隔離導入。LuaモードのDPMS呼び出しを修正したパッチは `tools/nwg-tools-lua.patch`。`~/.local/bin/nwg-displays` とユーザー用desktopエントリーから起動する。元のシステム版は残す。
- nwg-displaysの実際のGUI保存関数を使う7テストで、現在の配置・倍率・回転とworkspace出力を検証。画面の実変更はまだ実行していない。
- `~/.config/wallust/wallust.toml` と `templates/colors-hyprland.lua`、Waybar・AGS overview・wlogout・swayncのIPC呼び出しも移行対象。これらはHyprland設定の外部にあるため、Gitでこのリポジトリだけを戻しても復帰は完了しない。
- 動画壁紙の起動設定は `UserConfigs/Wallpaper.lua` に保存。設定メニュー・検索・Waybarランチャーは `hyprctl repl` から実効Lua変数を参照する。

### 再ログイン後の確認と修正

- 実セッションはHyprland 0.56.2、`configProvider=lua`、`backend=drm`。`configerrors` は空。
- `verify_live.py` で設定85項目、2画面の解像度・位置・倍率・回転、アニメーション全項目を移行前に対応するスナップショットと比較し、一致を確認。
- 静的キー160件と起動時のSuper+J/K/Oの3件、合計163件を確認。起動時の2スクリプトがJ/K解除・登録の間に割り込めて二重登録されていたため、`KeybindsLayoutInit.sh` を1回のLua IPCにまとめた。現在の実セッションにも適用し、重複が解消されたことを検証。
- 既存構成と同様、設定リロード後は起動時に追加したJ/K/Oが消える。今回の検証中にも160件へ戻ることを確認したため、作業後に同じレイアウトの初期化とJ/K初期化を再適用した。リロード時にも自動復元する設計変更は今回行っていない。
- Lua対応版Waybarは実行名が `.waybar-wrapped` となるため、`killall waybar` と `pgrep -x waybar` が対象を見つけない。表示切替・配色更新に関わる4スクリプトで通常版とNix版の両方を認識するよう修正。対象選択・SIGUSR2再読み込み・画面上の表示を確認。
- GhosttyはSuper+Enterのキー登録ではなく、フォントキャッシュの不整合による `FontconfigNoMatch` で終了していた。別キャッシュでの起動成功を確認後、`~/.cache/fontconfig` を作業ディレクトリの `fontconfig-before-repair/` へ退避し、システムの `fc-cache -f` で再生成。通常経路でウィンドウ生成と指定フォントの読み込みを確認し、ユーザーもSuper+Enterでの起動を確認した。フォント本体・Ghostty設定は変更していない。古いキャッシュの更新日時は移行配置より前であり、移行が元の不整合を作ったとは断定していない。
- ユーザーから残るフォント表示の問題はKittyのみと報告があり、追加のフォント対応は不要との指示により停止。
- IME、Waybar、hypridle、swww、swaync、AGS、ネットワーク・Bluetooth・Polkitの起動プロセスを確認。これは各機能の全操作を実機検証したという意味ではない。
- 未検証: 全ショートカットの手入力、マウス移動・リサイズ、テーマ・プリセット切替の全経路、nwg-displays GUIによる実際の保存・適用。

今回の回帰チェックは作業ディレクトリ内の `verify_live.py`、結果は `live-audit.json`。Ghosttyの失敗・成功ログも同じ場所に保存。

### バックアップと復帰

この作業のスナップショット・比較データ・ステージング・検証コードは次にある。

`$HOME/.local/state/hypr-lua-migration.Wgq0waj8`

配置済みファイルは `deployment.json`、元ファイルは `backup/`。復帰には次を実行してから再ログインする（表示不能の場合はTTYから実行）。

```sh
python3 "$HOME/.local/state/hypr-lua-migration.Wgq0waj8/deploy.py" --rollback
```

復帰時は変更後のファイルも別フォルダーへ退避してから元に戻す。関連ツールのユーザーラッパーも対象とし、システム版ツールは削除しない。

### 今後の上流更新

1. 稼働設定は個人設定を正とする。KooLの `copy.sh` / `upgrade.sh` を稼働設定に直接実行しない。
2. 上流を別ディレクトリで取得し、対象ファイルの差分とLua対応状況を確認する。
3. 必要な変更だけ作業用コピーへ取り込み、Hyprlandの検証と周辺スクリプトの呼び出しを確認してから反映する。
4. 形式や外部ツールの版が変わる場合は、外部設定も含めてバックアップし、実セッションで検証する。

完了条件は、Luaプロバイダーでの起動、設定エラーなし、現在の設定・登録キーバインド・画面配置・アニメーションとの対応確認、日常の切替操作と自動起動の実動作確認。準備だけで移行完了とは扱わない。

## 参照

- [公式Lua移行発表](https://hypr.land/news/26_lua/)
- [公式設定ガイド](https://wiki.hypr.land/Configuring/Start/)
- [Hyprland v0.56.2 Lua設定例](https://github.com/hyprwm/Hyprland/blob/v0.56.2/example/hyprland.lua)
- [Hyprland v0.56.2 IPC実装](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/debug/HyprCtl.cpp#L1043-L1076)
- [KooL後継リポジトリ](https://github.com/LinuxBeginnings/Hyprland-Dots)
- [nwg-displays 0.4.3](https://github.com/nwg-piotr/nwg-displays/releases/tag/v0.4.3)
- [nwg-displays 0.4.4](https://github.com/nwg-piotr/nwg-displays/releases/tag/v0.4.4)
- [Waybar Lua IPC対応](https://github.com/Alexays/Waybar/pull/5013)
- [Waybar設定プロバイダー検出修正](https://github.com/Alexays/Waybar/pull/5231)

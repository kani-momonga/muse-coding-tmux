# muse-coding-tmux

tmux の中でコーディングエージェント（Claude Code / Codex）を対話モードのまま駆動するための、設定とスクリプトのセットです。Muse（個人 AI エージェント）が別のコーディングエージェントへ作業を委任する、という運用のために作りました。人間が直接使う場合にもそのまま使えます。

> Run coding agents (Claude Code / Codex) interactively inside tmux, with hook-based guardrails and logs — built for an orchestrating agent (Muse) that delegates coding work and needs to *see* what the worker agent is doing.

## なぜ `-p`（非対話）ではなく tmux なのか

`claude -p "..."` のような非対話実行には、実運用で困る点があります。

- **承認待ちで黙って止まる**: git commit など一部の操作は承認が必要で、非対話だと誰も押せずに固まります。エラーにもならないので外から見分けがつきません
- **途中経過が見えない**: 出力は終了時にまとめて返るため、「作業中」と「停止中」の区別がつきません
- **引き継ぎが弱い**: 途中で落ちると、状態の復元は git の差分から推測するしかありません

tmux で対話モードを回すと、画面（pane）をいつでも読め、承認ダイアログにはキー送信で答えられ、セッション自体が残ります。そこに hook の保険を組み合わせるのがこのリポジトリの形です。

## 構成

| 部品 | 役割 |
|---|---|
| `bin/agent-tmux.sh` | tmux ドライバ。セッション起動・ブリーフ送信・画面キャプチャ・キー送信 |
| `claude/hooks/guard-bash.py` | Claude Code 用 PreToolUse hook。安全なコマンドは自動承認、危険な操作は拒否、それ以外は通常プロンプト |
| `claude/hooks/log-tool.py` | PostToolUse で全ツール実行を記録、Stop で完了イベントを記録 |
| `claude/settings.example.json` | 上記 hook の配線例（`~/.claude/settings.json` 用） |
| `codex/notify-agent.py` | Codex の `notify` 受け口。ターン完了イベントを記録 |
| `codex/config.example.toml` | Codex 側の設定例 |
| `examples/brief.example.md` | 委任ブリーフ（作業指示書）の雛形 |

ログはすべて `~/agent-runs/`（環境変数 `AGENT_RUNS_DIR` で変更可）に集まります。

- `<session>.pane.log` — tmux pane の全出力
- `tool-calls.log` — Claude Code のツール実行履歴（JSONL）
- `stop-events.log` / `last-stop.json` — Claude Code の完了イベント
- `codex-events.log` — Codex のターン完了イベント

**完了検知は推測ではなくイベントで**行えるのが要点です。「プロセスが生きている」ことと「仕事が進んでいる」ことは別物なので、完了は Stop / notify の記録と、git のコミットの移動で確認します。

## インストール

```bash
git clone https://github.com/kani-momonga/muse-coding-tmux.git
cd muse-coding-tmux
./install.sh
```

`install.sh` は次を行います（既存の設定ファイルは上書きしません）。

- `bin/agent-tmux.sh` を `~/bin/` へ
- hook スクリプトを `~/.claude/hooks/` へ、`notify-agent.py` を `~/.codex/` へ
- `~/.claude/settings.json` が無ければ example から作成（あればマージ手順を表示）
- Codex 用に `~/.codex/config.toml` へ追加する `notify` 行を表示

前提: tmux、python3、Claude Code および/または Codex がインストール済みであること。

## 使い方

```bash
# 1. セッションを起動（対象リポジトリのディレクトリでエージェントが立ち上がる）
agent-tmux.sh start claude mytask ~/path/to/repo
agent-tmux.sh start codex  mytask ~/path/to/repo

# 2. 初回ダイアログの処理（画面を見て、キーで答える）
agent-tmux.sh peek mytask          # 画面を確認
agent-tmux.sh keys mytask Enter    # 例: ダイアログに Enter で答える

# 3. ブリーフ（作業指示ファイル）を送る
agent-tmux.sh send mytask ./brief.md

# 4. 監視: 画面・ログ・完了イベント
agent-tmux.sh peek mytask 80
tail -f ~/agent-runs/tool-calls.log ~/agent-runs/stop-events.log

# 5. 終了
agent-tmux.sh kill mytask
```

起動時の承認モード:

- **Claude**: `--permission-mode acceptEdits`（ファイル編集は自動承認、Bash は hook＋プロンプトで制御）
- **Codex**: `--ask-for-approval on-request --sandbox workspace-write`（ワークスペース内はサンドボックスで自動、.git 書き込み等の昇格はプロンプト）

## 初回ダイアログについて

新しいディレクトリで起動すると、どちらのエージェントも初回だけ対話ダイアログを出します。これも `peek` と `keys` で処理できます。

- Claude Code: テーマ選択 → セキュリティ注意（Enter）→ フォルダ信頼（**既定は「No, exit」側**なので `Down` → `Enter`）
- Codex: フォルダ信頼（「Trust and continue」が選択済みなので `Enter`）

信頼済みのディレクトリでは信頼ダイアログは出ません。

## 安全モデル（guard-bash.py）

Claude Code の Bash は複合コマンドを `&&` / `;` / `|` で分割し、セグメント単位で判定します。

- **自動承認（allow）**: 全セグメントが許可リストに収まる場合のみ
  - git の読み取り（status / diff / log / show など）
  - リポジトリ内作業（add / commit / switch / checkout / fetch / pull / stash など）
  - feature ブランチへの push（`git push origin <branch>`、main/master は除く）
  - テスト・型チェック・lint（pnpm test、vitest、tsc、eslint、phpunit、pytest など）
  - 読み取り専用のシェルコマンド（ls / cat / grep / rg など）
- **拒否（deny）**: いずれかのセグメントが該当すれば全体を拒否
  - main / master への push、force push
  - `git reset --hard`、`git clean -f`、変更破棄系（checkout -- / restore）
  - `rm -rf`、`gh pr merge`、`wrangler deploy`、`sudo`
- **それ以外**: 何も返さず通常の承認プロンプトへ（tmux の画面で見て判断する）

「全部自動」でも「全部手動」でもなく、**頻出する安全な操作だけ自動化し、不可逆な操作は構造的に止め、残りは可視化する**のが狙いです。許可・拒否リストは `guard-bash.py` の `ALLOW_PATTERNS` / `DENY_PATTERNS` で調整できます。

Codex にはコマンド単位の PreToolUse hook に相当する仕組みがないため、保険は承認ポリシーとサンドボックスで寄せ、残りは tmux の可視性でカバーします。

## 注意点

- tmux セッションはマシン再起動や VM 入れ替えでは残りません。ただし Claude Code の会話記録は `~/.claude/projects/` に残るので `--resume` で復旧できます
- pane ログにはエージェントの出力がそのまま記録されます。機密情報を扱うタスクではログの取り扱いに注意してください
- hook は「保険」です。最終的な検証（テストの再実行、差分レビュー）は委任側の責任として別途行ってください

## ライセンス

MIT

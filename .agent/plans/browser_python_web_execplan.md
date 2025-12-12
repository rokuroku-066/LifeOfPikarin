# ブラウザ向けPython実装への移行計画

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

現行のC#シミュレーション（SpatialGridを用いたコロニー形成・繁殖・死亡を含む長時間稼働の箱庭）をPython実装へ移植し、Unityに依存せずブラウザ上で同じ挙動を観察できるようにする。固定タイムステップ・決定的な乱数・負のフィードバック（エネルギー消費、環境ストレス、過密抑制）を維持したまま、Python製シミュレーションコアとWebフロントエンド（Canvas描画＋リアルタイム更新）を提供し、長時間観察可能なデモを実行可能にする。

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here, even if it requires splitting a partially completed task into two (“done” vs. “remaining”). Use timestamps.

- [x] (2025-02-12 00:00Z) ExecPlan drafted and repository context reviewed.
- [x] (2025-02-12 00:00Z) Pythonシミュレーションコアの初期移植（SpatialGrid、World、Agent挙動）。
- [x] (2025-02-12 00:00Z) Python側ユニットテストと決定性検証を追加しパス。
- [x] (2025-02-12 00:00Z) Webサーバ（FastAPI/Starlette）とWebSocket/HTTPストリームによる状態配信を実装。
- [x] (2025-02-12 00:00Z) ブラウザCanvasレンダラと操作UI（開始/停止/リセット、速度設定、種設定ロード）を実装。
- [ ] (2025-02-12 00:00Z) 長時間安定性・パフォーマンス（1k+個体、60fps表示/30Hzシム）を確認しドキュメント化。
- [ ] (2025-02-12 00:00Z) 既存C#資産の最小限維持または移行方針の文書化（ビルド/テストの扱いを明記）。

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation. Provide concise evidence (short logs, measurements, or repro steps).

- Dotnet SDK はコンテナに未インストールで、C# テストは `dotnet` コマンド不在のため実行できない（`bash: command not found: dotnet`）。Python 版テストで決定性を確認済み。

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or at completion. Compare the result against the original purpose.

## Context and Orientation

- 現行シミュレーションは C#（.NET 8）で `src/Sim/` に実装され、`World.cs` が固定タイムステップ更新、SpatialGrid 近傍検索、グループ形成、繁殖・死亡・ストレス調整を司る。
- SpatialGrid 実装は `src/Sim/SpatialGrid.cs`、環境フィールドは `src/Sim/Environment.cs`、決定的乱数は `src/Sim/DeterministicRng.cs` にある。
- ヘッドレス実行は `src/SimRunner/`、Unityビューワは `src/Unity/` にあるが、本改修ではブラウザ表示に置き換える。
- 現行テストは `tests/SimTests/WorldTests.cs` がメトリクスやフィードバックの決定性を検証している。
- 重要な設計原則（`docs/DESIGN.md`、`AGENTS.md`）：Sim/View分離、固定Δt、負のフィードバック（密度/エネルギー/環境）、空間グリッドでの局所近傍のみ、決定的乱数。

## Plan of Work

Describe, in prose, the sequence of edits and additions. For each edit, name the file and location (function, module) and what to insert or change.

1. Pythonシミュレーション基盤を追加する: `src/python/terrarium/`（新規）に `vector.py`、`rng.py`、`spatial_grid.py`、`environment.py`、`config.py`、`world.py` を実装し、C#版と同等のデータ構造・更新ロジック（固定Δt、群れ形成、ライフサイクル、環境フィールド更新）を再現する。決定性のため乱数シードを受け取る。
2. 旧C#設定をPythonへ移植: `docs/DESIGN.md` と `src/Sim/Configs.cs` を参照し、Python用のデフォルト設定/パラメータローダを `config.py` と `presets/*.yaml` に用意。シード・初期個体数・フィードバック係数を保持する。
3. Pythonテストを整備: `tests/python/`（新規）にPytestベースのユニットテストを追加し、決定性（同シードで同結果）、人口・エネルギーメトリクス、SpatialGrid近傍取得、フィードバック（過密で死亡率上昇/繁殖抑制）を検証する。可能であれば C# テストケースを移植。
4. Web配信層を構築: `src/python/server.py` に FastAPI/Starlette ベースのAPIを実装し、WebSocketでシミュレーションスナップショット（位置、速度、グループ、状態）を送信。HTTPでプリセット取得・シミュレーション開始/停止/リセット制御を提供。非同期ループで固定Δtステップを回す。
5. ブラウザ表示を実装: `src/python/static/` に `index.html`, `app.js`, `styles.css` を追加し、Canvasでエージェントを矩形描画。WebSocketで受信したスナップショットを補間し、UI（開始/停止/リセットボタン、速度スライダー、シード入力）を提供。Sim/View分離を維持（フロントは状態読み取りのみ）。
6. 実行スクリプトと環境セットアップ: `pyproject.toml` か `requirements.txt` を追加して依存（fastapi, uvicorn, numpy等）を管理し、`make` か `python -m terrarium.server` で起動できるようにする。Docker/venv手順を README に追記。
7. 移行後のテスト/検証フローを文書化: 既存 `dotnet test tests/SimTests/SimTests.csproj` の取り扱い（非対応なら理由）と、新規 Python テスト/起動手順を README/ドキュメントへ追記。旧 Unity 表示の代替としてブラウザアクセス方法を説明し、長時間安定性チェック手順を記載。
8. 不要/重複するC#側エントリポイントの扱いを決定: SimRunner/Unity部分はそのまま残すが既存デフォルトに影響しないよう分離するか、Python移行を優先的に案内する文書を追加する。

## Concrete Steps

State the exact commands to run and where to run them (working directory). When a command generates output, show a short expected transcript so the reader can compare. This section must be updated as work proceeds.

- (環境) `python -m venv .venv && source .venv/bin/activate` で仮想環境を作成。
- (依存) `pip install -r requirements.txt` で依存を導入（FastAPI, uvicorn, numpy, pytest 等）。
- (C#確認) `dotnet --info` と `dotnet test tests/SimTests/SimTests.csproj` を可能な限り実行し、Python移行後もビルド可否を記録。
- (Pythonテスト) `pytest tests/python` で新規テストを実行。
- (開発サーバ) `uvicorn terrarium.server:app --reload --port 8000` を起動し、ブラウザで `http://localhost:8000` を開く。

## Validation and Acceptance

Describe how to start or exercise the system and what to observe. Phrase acceptance as behavior, with specific inputs and outputs.

- 決定性: 同一シード・設定で `pytest tests/python/test_world.py::test_deterministic_steps` を2回実行すると同一メトリクス配列が得られる。
- パフォーマンス: 1,000体を30Hzで5,000ステップ進めた場合でも1ステップ平均 tick 時間が ~5ms 以下（ローカルCPUベース）で推移することをログで確認。`python -m terrarium.headless --steps 5000 --agents 1000` の出力に平均tick時間を記録する。
- 長期安定性: 30分相当（例: 50,000ステップ）を headless 実行し、人口が無限増殖または即全滅せず、出生・死亡が周期的に推移することをメトリクスで確認。負のフィードバック（過密で出生抑制/ストレス死）が発火しているログを確認。
- Sim/View分離: Webフロントは読み取り専用であることをコード上で確認（WebSocket送信はサーバのみ、クライアントから状態変更はAPI経由）。
- No O(N²): 近傍探索は `spatial_grid.py` のセル近傍検索のみを使い、全ペア走査が無いことをレビューで確認。
- ブラウザ観察: サーバ起動後、Canvas上でキューブ（エージェント）が滑らかに移動・集団形成すること、再生/停止/リセット操作が機能することを目視。

## Idempotence and Recovery

- 仮想環境・依存インストールは再実行しても副作用は限定的。`pip install -r requirements.txt --upgrade` で更新可能。
- サーバ/テストコマンドは何度でも再実行可能。WebSocket接続は切断時に自動再接続する実装とする。
- データ破壊の可能性がある操作はないが、設定変更時は `config.yaml` をコミットし、既定値を README に明示。

## Artifacts and Notes

Include the most important transcripts, diffs, or snippets as indented examples. Keep this section updated with notable logs (性能計測、長期安定性のメトリクスなど)。

## Interfaces and Dependencies

- Pythonパッケージ: FastAPI/Starlette, Uvicorn, Numpy（ベクトル計算用、必要に応じてPure Python fallback）、PyYAML（設定読み込み）。
- 新規モジュール: `terrarium` パッケージに `world`, `agent`, `spatial_grid`, `environment`, `rng`, `config`, `server`, `headless` を含める。
- Webクライアント: `static/app.js` が WebSocket `ws://<host>/ws` に接続し、受信したスナップショットを Canvas へ描画。UI操作は REST (`/api/control/start|stop|reset`) を呼び出す。
- C#資産: 既存コードは`src/Sim`以下に残る。Python移行後の推奨パスと互換性メモを README に追記し、.NET テスト実行可否を明記する。

## Extra acceptance checklist (repo-specific)

- パフォーマンス sanity: 1kエージェントで30Hz tick時にtick時間平均5ms以下を目指し、計測結果を`Artifacts and Notes`に記録。
- 長期安定性: 過密時の負のフィードバックが機能し人口が振動的に推移するメトリクスを提示。
- No O(N²): 空間グリッドの3x3近傍走査のみで相互作用する設計を保持。
- Sim/View分離: Pythonサーバがシミュレーションを駆動し、ブラウザは読み取りのみで状態を書き換えないことを確認・記述。

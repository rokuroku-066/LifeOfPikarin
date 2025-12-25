[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/rokuroku-066/LifeOfPikarin)

# Life Of Pikarin

俯瞰カメラでキューブの群れが動く Phase 1 をベースに、Phase 2 では **ぴかりん静的モデル + 背景（床+壁2面） + 斜め固定カメラ** のビューアへ移行中です。シミュレーションは固定 Δt で決定論的に進み、描画は Three.js の GPU インスタンシングで行います（Sim → View の一方向）。

## 特徴（Phase 1）

- **固定ステップ & 決定性**: `time_step=1/50` 秒で進行し、同一 seed なら結果が再現可能。
- **Sim/View 分離**: シミュレーションは `World.step` が単独で進め、ブラウザは WebSocket 受信結果を補間描画するだけ。
- **SpatialGrid で O(N²) 回避**: 近傍は自身のセルと隣接セルのみを探索し、precomputed オフセットで距離計算を抑制。
- **長期安定のフィードバック**: 密度ストレス・疾病確率・エネルギー代謝・繁殖抑制で暴走や全滅を防止。
- **グループダイナミクス**: 未所属からの自律的な形成、近傍多数派への乗換、分裂、拠点吸引をサポート。社会トレイト（`sociality` など）で採用/離脱の傾向が変化。
- **環境フィールド**: 食料・危険・フェロモンをセルグリッドで管理し、`environment_tick_interval` ごとに拡散・減衰・再生。
- **ビューア**: Three.js の `InstancedMesh` で 1 画面の斜め固定カメラを描画。UI は Start/Stop/Reset/速度変更のみで Sim には書き込まない。

## リポジトリ構成

```text
.
├── AGENTS.md             # Codex 向けガイド
├── .agent/PLANS.md       # ExecPlan 運用ルール
├── docs/
│   ├── DESIGN.md         # Phase 1 設計の詳細
│   └── snapshot.md       # WebSocket スナップショット仕様
├── src/terrarium/        # Python 製シミュレーション & FastAPI + Three.js ビューア
│   ├── app/
│   │   ├── headless.py   # CLI ランナー（CSV/JSON 出力）
│   │   ├── server.py     # FastAPI + WebSocket 配信
│   │   └── static/       # index.html / app.js (Three.js)
│   └── sim/
│       ├── core/         # World/Agent/Config 等のコア
│       ├── systems/      # 群れ・操舵・ライフサイクルなどのシステム分割
│       ├── types/        # Snapshot/Metrics などの型
│       └── utils/        # 数学ユーティリティ
├── tests/python/         # 決定性と安定性のユニットテスト
├── tests/js/             # ビュー用ユーティリティの Node テスト
├── requirements.txt
└── pyproject.toml
```

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate  # Windows は .venv\Scripts\activate
pip install -r requirements.txt
```

Three.js のユーティリティをテストする場合は Node.js 20+ を用意してください（追加の npm インストールは不要）。

## ヘッドレス実行（CSV/JSON ログ）

```bash
python -m terrarium.app.headless \
  --steps 5000 \
  --seed 42 \
  --log tests/artifacts/metrics.csv \
  --log-format detailed \
  --summary tests/artifacts/summary.json
```

- `--deterministic-log` を付けると `tick_ms=0.000` 固定の決定論的 CSV を生成（同 seed なら完全一致）。
- `--log-format basic` は最低限のカラム（tick/population/births/deaths/avg_energy/avg_age/groups/neighbor_checks/tick_ms）。
- `--log-format detailed` は密度関連（ungrouped、group サイズ、セル占有）、ストレス、速度、stride 状態などを追加。
- `--summary` は末尾 `--summary-window` tick のパーセンタイル・相関・ピークを JSON で書き出します。

主要なパラメータは `src/terrarium/sim/core/config.py` の `SimulationConfig` 配下にあります。`SimulationConfig.from_yaml(path)` で外部 YAML を読み込むこともできます。

## Web ビューア（Three.js）

```bash
uvicorn terrarium.app.server:app --reload --port 8000
```

- ブラウザで `http://localhost:8000` を開くと斜め固定カメラの 1 画面が表示されます。
- `/api/control/start|stop|reset|speed` がシミュレーション制御、`/ws` がスナップショット配信（クライアント側から状態変更は行わない）。
- ピクセル比制限と影オフで大規模インスタンスでも描画負荷を抑えています。`src/terrarium/app/static/assets/` に本番の GLB/テクスチャ（`pikarin.glb`, `ground.png`, `wall_back.png`, `wall_side.png`）を配置してください。ネットワークが無い場合は `src/terrarium/app/static/app.js` の Three.js import をローカルに置き換えてください。

## バリデーション

- Python テスト（必須）

  ```bash
  pytest tests/python
  ```

- Three.js ユーティリティのテスト（任意）

  ```bash
  npm run test:js
  ```

- 長時間確認の推奨コマンド

  ```bash
  python -m terrarium.app.headless --steps 5000 --seed 42 --log tests/artifacts/metrics.csv --log-format detailed --summary tests/artifacts/summary.json
  ```

## 参考ドキュメント

- 設計詳細とアルゴリズム: [`docs/DESIGN.md`](docs/DESIGN.md)
- スナップショット仕様: [`docs/snapshot.md`](docs/snapshot.md)
- ExecPlan の運用ルール: [`.agent/PLANS.md`](.agent/PLANS.md)
- 長時間観察時のメトリクスやフィードバックの検証手順は `AGENTS.md` も参照してください。

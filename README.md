# Life Of Pikarin

俯瞰固定カメラでキューブたちが決定的に動き回る箱庭ライフゲーム風シミュレーションです。Phase 1 は **キューブ表示のみ** を対象とし、後から FBX モデル・アニメーションに差し替え可能な構造になっています。

- シミュレーションは **長時間連続稼働** を想定
- 個体は成長・繁殖・死などのライフサイクルを持つ
- SpatialGrid を用いた近傍検索で **O(N^2) を回避**
- 複数のグループ（コロニー）が自然に形成されるようなルール設計
- 表示は Phase 1 では **キューブ＋GPU インスタンシング**
- Codex 用の `AGENTS.md` / `.agent/PLANS.md` と連携

詳細なシステム設計は [`docs/DESIGN.md`](docs/DESIGN.md) を参照してください。

---

## プロジェクトの現状

- **Simulation (Python)**: `src/terrarium/` に固定Δt・SpatialGrid・フィードバック付きの Python 実装を収録。FastAPI ベースの Web ビューアで Unity なしにブラウザから観察可能。
- **Visualization**: ブラウザ用 Three.js レンダラ（GPU インスタンシング/Points）を `src/terrarium/static/` に同梱。サーバー側でシミュレーションを進め、クライアントはスナップショットを受信して描画するだけです（Sim→View の一方向）。
- **Headless 実行**: `python -m terrarium.headless` でメトリクスを CSV 出力し、長時間の安定性を確認できます。
- **テスト**: `tests/python/` に決定性・上限チェック・SpatialGrid のユニットテストがあります。

---

## 開発環境

| 目的 | 推奨ツール | 備考 |
| --- | --- | --- |
| シミュレーション実行・ブラウザ表示 | **Python 3.11+** | `python -m venv .venv` で仮想環境を作り、`pip install -r requirements.txt` で依存を導入 |
| サーバー起動 | **uvicorn** | `pip install -r requirements.txt` に含まれています |
| バージョン管理 | Git | 任意のクライアントで OK |

---

## ディレクトリ構成

```text
.
├── AGENTS.md             # Codex 向けガイド
├── .agent/PLANS.md       # ExecPlan の運用ルール
├── docs/DESIGN.md        # システム設計（Simulation / View / Grid 等）
├── src/
│   └── python/           # Python 製シミュレーションと Web ビューア
├── tests/python/         # Python シミュレーションのユニットテスト
├── pyproject.toml        # Python パッケージ定義
└── requirements.txt      # 依存パッケージ一覧
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone https://github.com/rokuroku-066/LifeOfPikarin.git
   cd LifeOfPikarin
   ```
2. Python 依存をインストール（推奨: 仮想環境）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows は .venv\Scripts\activate
   pip install -r requirements.txt
   ```

---

## シミュレーションの実行（ヘッドレス）

Python 製のヘッドレスランナーでステップ単位のシミュレーションを回し、CSV にメトリクスを書き出します。

```bash
python -m terrarium.headless --steps 3000 --seed 42 --initial 120 --max 500 --log artifacts/metrics_smoke.csv
```

出力される CSV のカラム例:

- `tick`: シミュレーションステップ
- `population`: 生存個体数
- `births` / `deaths`: ステップ中の出生・死亡数
- `avgEnergy` / `avgAge`: 平均エネルギー・平均年齢
- `groups`: グループ（群れ）数（初期は 0。未所属の個体はカウントしない）
- `neighborChecks`: 近傍判定のカウント（O(N^2) を避けるためのヘルス指標）
- `tickDurationMs`: 1 ステップの処理時間（ミリ秒）

`--log` で指定したパス配下にディレクトリが無ければ自動で作成されます。主要な調整パラメータ（`terrarium.config.SimulationConfig` に対応）:
- エネルギー上限と代謝: `EnergySoftCap`, `HighEnergyMetabolismSlope`, `MetabolismPerSecond`, `InitialEnergyFractionOfThreshold`
- 繁殖トリガ: `ReproductionEnergyThreshold`, `AdultAge`, `DensityReproductionSlope`, `DensityReproductionPenalty`
- 寿命/危険: `BaseDeathProbabilityPerSecond`, `AgeDeathProbabilityPerSecond`, `DensityDeathProbabilityPerNeighborPerSecond`
- 環境フィールド: `FoodRegenPerSecond`, `FoodFromDeath`, `DangerDiffusionRate` / `DangerDecayRate`, `PheromoneDepositOnBirth`
- グループ形成・分離: `GroupFormationWarmupSeconds`, `GroupFormationChance`, `GroupAdoptionChance`, `GroupSplitChance` など（初期グループ数は 0）

---

## ブラウザ表示付きの Python 版

Unity を起動せずにブラウザで観察できる Python 実装を `src/terrarium/` に追加しています。

### セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Web ビューアの起動

```bash
uvicorn terrarium.server:app --reload --port 8000
```

- ブラウザで `http://localhost:8000` を開くと Three.js 上にキューブ（インスタンス）が表示されます。
- Start/Pause/Reset ボタンと速度スライダーでサーバ側のシミュレーションを制御します（Sim → View の一方向）。
- WebSocket (`/ws`) がスナップショットを定期配信し、クライアントは状態を書き換えません。

### Three.js ビューアについて

- Web UI は CDN から提供される ES Module 版 Three.js (`https://unpkg.com/three@0.164.1/...`) を読み込み、`OrbitControls` でパン・ズームできます（回転は無効化）。
- レンダラはオーソグラフィックビューでワールドの中心にカメラを置き、スナップショットを `InstancedMesh` の行列と色に反映します。
- ウィンドウリサイズ時に投影行列とキャンバスサイズが更新されます。ネットワークが無い場合は Three.js モジュールをローカルに配置し、`src/terrarium/static/app.js` のインポート先を差し替えてください。

### テスト

```bash
pytest tests/python
```

- 同一シードでの決定性、SpatialGrid の近傍取得、個体数の上限チェックをカバーしています。

---

## テスト

シミュレーションコアの決定性や安定性は Python ユニットテストで確認できます。

```bash
pytest tests/python
```

- 固定シードでの結果一致、近傍検索の範囲制限、負のフィードバックによる個体数抑制、メトリクス CSV 出力などをカバーしています。

### 環境フィールド

`EnvironmentGrid` はセル毎に `food`・`pheromone`（グループ別）・`danger` の 3 スカラーフィールドを持ち、毎ステップで減衰と隣接セルへの拡散を行います。

- `food`: パッチ定義で初期化され、時間経過で再生・拡散し、消費や死亡で追加されます。`World.Step` の Forage 行動は `food` 勾配を優先。
- `pheromone`: 繁殖成功地点で自グループのフェロモンを撒き、グループ固有の濃度勾配が Cohesion に寄与します。
- `danger`: 敵接近や危険サインで蓄積され、勾配や局所濃度が高いセルではエージェントが Flee 行動を選好します。

---

## ドキュメントと運用

- 設計思想・アルゴリズムの詳細: [`docs/DESIGN.md`](docs/DESIGN.md)
- ExecPlan の書き方・運用ルール: [`.agent/PLANS.md`](.agent/PLANS.md)
- 長時間観察時のメトリクスやフィードバックの検証手順は `AGENTS.md` も参照してください。

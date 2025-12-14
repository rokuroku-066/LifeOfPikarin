# Life Of Pikarin

俯瞰固定カメラでキューブたちが決定的に動き回る箱庭ライフゲーム風シミュレーションです。Phase 1 は **キューブ表示のみ** を対象とし、後から FBX モデル・アニメーションに差し替え可能な構造になっています。

- シミュレーションは **長時間連続稼働** を想定
- 個体は成長・繁殖・死などのライフサイクルを持つ
- SpatialGrid を用いた近傍検索で **O(N^2) を回避**
- ワールド境界は反射（壁で位置を折り返し、速度を反転）し、領域外にはみ出さない
- 複数のグループ（コロニー）が自然に形成されるようなルール設計
- 高密度ペナルティを緩め（soft cap 22、密度繁殖係数 0.6、疾病・死亡の密度係数を半減）、同グループが密集しやすいが `personal_space` で重なりは防ぐ
- 近距離仲間が一定時間いないままの所属エージェントは、新しいグループとして分離して再コロニー化し（確率 `group_detach_new_group_chance`）、放浪状態に落ちないようにする
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
- フィールド更新頻度: `EnvironmentTickInterval`（既定 0.12 秒）。食料/危険/フェロモンの拡散・減衰をこの周期でまとめて処理し、CPU 負荷を抑えます。
- 初期/最大個体数: `initial_population` 240, `max_population` 500（スナップショットサイズと近傍計算コストを抑制）。
- 境界バイアス: `boundary_margin` 内では `boundary_avoidance_weight` で内側へ押し戻し、`boundary_turn_weight` で進行方向を内向きに寄せ、反射境界と併用して滑らかに折り返します。
- ランダム歩行の更新周期: `wander_refresh_seconds`（SpeciesConfig, 既定 0.12 秒）。この周期で各個体のランダム方向を更新し、RNG 呼び出しを削減します。
- 孤立時の再コロニー化: 近距離の味方が一定秒数見つからない場合は `group_switch_chance` で近傍多数派へ乗り換え、閾値を満たさなければ `group_detach_new_group_chance` で新グループを立ち上げ、それも外れれば一旦未所属に戻ります。
- グループ形成・分離: `GroupFormationWarmupSeconds`, `GroupFormationChance`, `GroupAdoptionChance`, `GroupSplitChance` に加え、近傍の同グループ人数に比例して分裂確率を上乗せする `GroupSplitSizeBonusPerNeighbor` と上限 `GroupSplitChanceMax`、サイズ起因ストレス係数 `GroupSplitSizeStressWeight`、分裂時に巻き込む仲間数 `GroupSplitRecruitmentCount`、分裂/合流後の多数派への再統合を一定時間抑える `GroupMergeCooldownSeconds`、味方が周囲にいるとき多数派への乗り換えを止める `GroupAdoptionGuardMinAllies` など（初期グループ数は 0）
- グループ内の繁殖抑制: `GroupReproductionPenaltyPerAlly`（同グループ近傍1人あたりの繁殖率低下量）と `GroupReproductionMinFactor`（下限）。大きなグループに属しているほど個体の繁殖確率が下がり、コロニーサイズの自律分散を促します。
- 群れ間距離/結束: `ally_cohesion_weight`, `ally_separation_weight`, `other_group_separation_weight`, `other_group_avoid_radius`, `other_group_avoid_weight`（同グループは密集、異グループは早めに距離を取る調整用）

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

- Web UI は CDN から提供される ES Module 版 Three.js (`https://unpkg.com/three@0.164.1/...`) を読み込みます。右上の斜めカメラは `OrbitControls` でパン / ズーム / 回転できます（Sim には一切書き込まない）。
- 画面は 3 分割です: 左 = 真上オーソグラフィック、右上 = フィールド端からのパース付き斜めビュー、右下 = ランダムに選ばれた個体の POV（個体が消滅したら自動で別個体に切替）。
- 単一の `InstancedMesh` を共有し、scissor viewport で 3 つのカメラをレンダリングします。スナップショットの行列と色のみを更新するため View 側で O(N²) にはなりません。
- パフォーマンス対策としてピクセル比を `min(devicePixelRatio, 1.5)` に制限し、影描画を無効化して GPU 負荷を抑えています。大規模インスタンスでもフレーム時間を安定させる狙いです。
- ウィンドウリサイズ時に投影行列とキャンバスサイズが更新されます。ネットワークが無い場合は Three.js モジュールをローカルに配置し、`src/terrarium/static/app.js` のインポート先を差し替えてください。

### テスト

```bash
pytest tests/python
npm run test:js
```

- 同一シードでの決定性、SpatialGrid の近傍取得、個体数の上限チェックをカバーしています。
- Web ビュー用のユーティリティ（グループ色計算）の決定性を Node 組み込みのテストランナーで検証します（`npm run test:js` が内部で `node --test "tests/js/**/*.js"` を呼ぶので PowerShell / bash どちらでも同一コマンドで動作）。

---

## テスト

シミュレーションコアの決定性や安定性は Python ユニットテストで確認できます。

```bash
pytest tests/python
npm run test:js
```

- 固定シードでの結果一致、近傍検索の範囲制限、負のフィードバックによる個体数抑制、メトリクス CSV 出力などをカバーしています。
- Three.js ビュー向けの色ユーティリティについて、グループ ID に対する色相の正規化・ラップアラウンドの挙動を確認できます（`npm run test:js` 経由で `node --test "tests/js/**/*.js"` を実行するクロスプラットフォーム構成）。

### 環境フィールド

`EnvironmentGrid` はセル毎に `food`・`pheromone`（グループ別）・`danger` の 3 スカラーフィールドを持ち、毎ステップで減衰と隣接セルへの拡散を行います。

- `food`: パッチ定義で初期化され、時間経過で再生・拡散し、消費や死亡で追加されます。`World.Step` の Forage 行動は `food` 勾配を優先。
- `pheromone`: 繁殖成功地点で自グループのフェロモンを撒き、グループ固有の濃度勾配が Cohesion に寄与します。拡散はワールド境界にクランプされ、`pheromone_decay_rate` > 0（デフォルト 0.05）で長時間走行時もフィールドサイズが暴走しません。
- `danger`: 敵接近や危険サインで蓄積され、勾配や局所濃度が高いセルではエージェントが Flee 行動を選好します。

---

## ドキュメントと運用

- 設計思想・アルゴリズムの詳細: [`docs/DESIGN.md`](docs/DESIGN.md)
- ExecPlan の書き方・運用ルール: [`.agent/PLANS.md`](.agent/PLANS.md)
- 長時間観察時のメトリクスやフィードバックの検証手順は `AGENTS.md` も参照してください。

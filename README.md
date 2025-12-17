[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/rokuroku-066/LifeOfPikarin)
 # Life Of Pikarin

俯瞰固定カメラでキューブたちが決定的に動き回る箱庭ライフゲーム風シミュレーションです。Phase 1 は **キューブ表示のみ** を対象とし、後から FBX モデル・アニメーションに差し替え可能な構造になっています。

- シミュレーションは **長時間連続稼働** を想定
- 個体は成長・繁殖・死などのライフサイクルを持つ
- SpatialGrid を用いた近傍検索で **O(N^2) を回避**
- ワールド境界は反射（壁で位置を折り返し、速度を反転）し、領域外にはみ出さない
- 複数のグループ（コロニー）が自然に形成されるようなルール設計
- 高密度では繁殖抑制・ストレス・疾病などの負のフィードバックで暴走を防ぎ、`personal_space` / `min_separation_*` で近距離の重なりも抑える
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
├── docs/                 # システム設計（Simulation / View / Grid 等）
│   ├── DESIGN.md
│   └── snapshot.md       # WebSocket スナップショット仕様
├── src/
│   └── terrarium/        # Python 製シミュレーション + FastAPI/WS + Three.js ビューア
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
python -m terrarium.headless --steps 5000 --seed 42 --log artifacts/metrics_smoke.csv
```

決定論的な CSV（同じ seed で 2 回回したときに完全一致させたい）を取りたい場合は `--deterministic-log` を付けてください。`tick_ms` は 0.000 に固定され、残りの値が同一 seed で一致します。

出力される CSV のカラム例:

- `tick`: シミュレーションステップ
- `population`: 生存個体数
- `births` / `deaths`: ステップ中の出生・死亡数
- `avg_energy` / `avg_age`: 平均エネルギー・平均年齢
- `groups`: グループ（群れ）数（初期は 0。未所属の個体はカウントしない）
- `neighbor_checks`: 近傍判定のカウント（O(N^2) を避けるためのヘルス指標）
- `tick_ms`: 1 ステップの処理時間（ミリ秒）。壁時計時間なので通常は実行ごとに変わります（`--deterministic-log` では 0.000）。

`--log` で指定した出力先ディレクトリは事前に作成してください。主要な調整パラメータは `src/terrarium/config.py` の `SimulationConfig` / `SpeciesConfig` / `EnvironmentConfig` / `FeedbackConfig` にまとまっています:

- エネルギー上限と代謝: `energy_soft_cap`, `high_energy_metabolism_slope`, `metabolism_per_second`, `initial_energy_fraction_of_threshold`
- 繁殖トリガ: `reproduction_energy_threshold`, `adult_age`, `density_reproduction_slope`, `density_reproduction_penalty`
- 寿命/密度死亡: `base_death_probability_per_second`, `age_death_probability_per_second`, `density_death_probability_per_neighbor_per_second`
- 環境フィールド: `food_regen_per_second`, `food_from_death`, `pheromone_diffusion_rate` / `pheromone_decay_rate`, `pheromone_deposit_on_birth`
- フィールド更新頻度: `environment_tick_interval`（既定 0.36 秒）。食料/フェロモン等の拡散・減衰をこの周期でまとめて処理し、CPU 負荷を抑えます。
- 初期/最大個体数: `initial_population`（既定 260）, `max_population`（既定 700）。初期ブートストラップモードは廃止し、最初の tick から SpatialGrid で近傍を構築しつつ通常の群形成/フィードバックを適用します。
- 境界バイアス: `boundary_margin` 内では `boundary_avoidance_weight` で内側へ押し戻し、`boundary_turn_weight` で進行方向を内向きに寄せ、反射境界と併用して滑らかに折り返します。
- ランダム歩行の更新周期: `wander_refresh_seconds`（既定 0.14 秒）。この周期で各個体のランダム方向を更新し、RNG 呼び出しを削減します。
- 近距離の押し返し: `personal_space_radius`, `personal_space_weight`, `min_separation_distance`, `min_separation_weight`
- 孤立時の再コロニー化: 近距離の味方が一定秒数見つからない場合は `group_switch_chance` で近傍多数派へ乗り換え、閾値を満たさなければ `group_detach_new_group_chance` で新グループを立ち上げます（外れた場合は未所属に戻る）。
- グループ形成・分離: `group_formation_warmup_seconds`, `group_formation_chance`, `group_adoption_chance`, `group_split_chance`, `group_split_size_bonus_per_neighbor`, `group_split_chance_max`, `group_split_recruitment_count`, `group_merge_cooldown_seconds`, `group_adoption_guard_min_allies` など
- グループ上限: `feedback.max_groups`（既定 10）。上限を超える新規グループ生成を抑止し、長時間回帰テストの範囲内に収めます。
- グループ内の繁殖抑制: `group_reproduction_penalty_per_ally`（同グループ近傍1人あたりの繁殖率低下量）と `group_reproduction_min_factor`（下限）
- 拠点（group base）への弱い引力: `group_base_attraction_weight`, `group_base_dead_zone`, `group_base_soft_radius`
- 群れ間距離/結束: `ally_cohesion_weight`, `ally_separation_weight`, `other_group_separation_weight`, `other_group_avoid_radius`, `other_group_avoid_weight`（同グループは密集、異グループは早めに距離を取る調整用）
- 進化設定: `evolution.enabled`（既定 False）で遺伝的形質伝搬を有効化。`mutation_strength` と `lineage_mutation_chance`、各トレイトの `clamp` 範囲、重み（`*_mutation_weight`）で変異幅を調整し、無効時は既存 RNG 消費と挙動を変えません。

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
- 環境フィールドの食品・フェロモン可視化オーバーレイは廃止し、キューブ本体のみを描画します。
- パフォーマンス対策としてピクセル比を `min(devicePixelRatio, 1.5)` に制限し、影描画を無効化して GPU 負荷を抑えています。大規模インスタンスでもフレーム時間を安定させる狙いです。
- ウィンドウリサイズ時に投影行列とキャンバスサイズが更新されます。ネットワークが無い場合は Three.js モジュールをローカルに配置し、`src/terrarium/static/app.js` のインポート先を差し替えてください。

### テスト

```bash
pytest tests/python
npm run test:js
```

- 同一シードでの決定性、SpatialGrid の近傍取得、個体数の上限チェック、5000 tick の長時間パフォーマンス回帰（人口ピーク 400～500、グループ 5～10、tick 平均 25ms 以下）をカバーしています。長時間テストは環境によっては 1 分強かかるため、実行前に十分な時間を確保してください。
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

`EnvironmentGrid` はセル毎に `food`・`pheromone`（グループ別）の 2 スカラーフィールドを持ち、毎ステップで減衰と隣接セルへの拡散を行います。

- `food`: パッチ定義で初期化され、時間経過で再生・拡散し、消費や死亡で追加されます。`AgentState.SEEKING_FOOD` では `food` 勾配を優先します。
- `pheromone`: 繁殖成功地点で自グループのフェロモンを撒き、グループ固有の濃度勾配が Cohesion に寄与します。拡散はワールド境界にクランプされ、`pheromone_decay_rate` > 0（デフォルト 0.05）で長時間走行時もフィールドサイズが暴走しません。

---

## ドキュメントと運用

- 設計思想・アルゴリズムの詳細: [`docs/DESIGN.md`](docs/DESIGN.md)
- ExecPlan の書き方・運用ルール: [`.agent/PLANS.md`](.agent/PLANS.md)
- 長時間観察時のメトリクスやフィードバックの検証手順は `AGENTS.md` も参照してください。

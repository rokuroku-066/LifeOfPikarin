# 長期稼働キューブ・テラリウム設計（Phase 1 完成版）

現在の Python 実装とブラウザビューア（three.js ベース）の挙動に一致するよう、Phase 1 の完成形として設計をまとめ直しました。Phase 2 以降（FBX/アニメーション置き換え）は扱わず、キューブ表示のみを対象にします。

## 0. 目的と基本原則

- **長期安定稼働**: 固定 Δt（既定 1/50 秒）で決定論的に進み、seed を与えると同一ステップ列を再現できる。
- **Sim/View の分離**: シミュレーションは `World.step` でのみ状態を進め、View は WebSocket スナップショットを補間描画するだけ。View のフレーム時間や UI 操作は Sim を遅らせない。
- **O(N²) 回避**: 空間検索は `SpatialGrid` の近傍セルのみ。precomputed オフセットと半径²で距離計算を最小化する。
- **負のフィードバック**: 近傍密度によるストレス・疾病確率、エネルギー代謝、繁殖抑制、加齢・基礎ハザードで人口爆発と全滅の両方を防ぐ。

## 1. コンポーネント概要

- **Simulation Core (`src/terrarium/sim/core/world.py`)**: エージェント更新、グループダイナミクス、ライフサイクル計算、環境フィールド適用、メトリクス記録を担当。
- **Environment (`src/terrarium/sim/core/environment.py`)**: 食料・危険・フェロモンをセルグリッドで管理し、拡散/減衰/再生をまとめて実行。リソースパッチと決定論的気候ノイズをサポート。
- **Spatial Hash (`src/terrarium/sim/core/spatial_grid.py`)**: 近傍セルだけを走査する Uniform Grid。事前計算済みセルオフセットを使う `collect_neighbors_precomputed` が per-agent ループを支える。
- **RNG (`src/terrarium/sim/core/rng.py`)**: `DeterministicRng` で seed 固定の乱数を供給。気候ノイズは別ストリーム（seed + salt）。
- **Headless ランナー (`src/terrarium/app/headless.py`)**: CLI でステップを回し、CSV/JSON にメトリクスを出力して長期安定性を確認。
- **Web サーバー (`src/terrarium/app/server.py`)**: FastAPI + WebSocket。`/api/control/{start,stop,reset,speed}` で制御し、`/ws` がスナップショットを配信。
- **View (`src/terrarium/app/static/app.js`)**: Three.js の `InstancedMesh` でキューブを 3 ビュー（俯瞰・斜め・POV）描画。スナップショットを補間し、色/スケールに状態をマップ。

## 2. 状態と設定

- **ワールド**: 正方形 `world_size=100`、反射境界。`boundary_margin` 内は内向きバイアスで折り返しを滑らかにする。
- **時間**: `time_step` で固定進行。`environment_tick_interval`（既定 6 秒）単位でフィールド更新をバッチ処理。
- **グリッド**: `cell_size=5.5` の SpatialGrid を共有（環境も同セル幅）。
- **初期個体**: `initial_population=200` をランダム配置・速度でブートストラップ。`max_population=700` を超えてスポーンしない。
- **エージェント状態**: 位置/速度/heading、エネルギー、年齢、ストレス、グループ ID（未所属は -1）、ワンダー方向と残時間、孤立秒数、グループクールダウン。
- **形質（`AgentTraits`）**: `speed` / `metabolism` / `disease_resistance` / `fertility` に加え `sociality` / `territoriality` / `loyalty` / `founder` / `kin_bias`。`EvolutionConfig` に従い変異・クランプし、`trait_mutation_chance` と `mutation_strength`、各ウェイトで揺らぐ。系譜は `lineage_id` を持ち、必要に応じて新規割り当て。
- **サイズ算出**: 成熟度（`adult_age`）とエネルギーを 0.4〜1.0 のスケールにマップし、スナップショットへ出力。

## 3. 1 tick の処理フロー (`World.step`)

1. ペンディングのフィールドイベントバッファをクリアし、`SpatialGrid` に生存個体を再インサート。グループ人数を集計。
2. 人口が多い場合は **ストライド更新** を有効化: `group_update_stride` / `steering_update_stride` と閾値を基に、グループ処理や Steering を tick+id で間引く（決定論的）。
3. 各エージェントについて近傍収集（事前計算セルオフセット＋半径²）し、グループ更新・Steering・ライフサイクルを行う（詳細は後述）。
4. 誕生キューを取り込み、死亡個体を除去。アクティブグループを集約し、孤立したグループ拠点を剪定。
5. 食料/危険/フェロモンのペンディングイベントを環境に適用し、`environment_tick_interval` ごとに拡散・減衰・再生・ノイズ更新を実行。
6. `TickMetrics` を生成して最新の1件のみ保持（tick 時間、人口、出生/死亡、平均エネルギー・年齢、グループ数、近傍チェック数、未所属数）。

## 4. グループダイナミクス

- **形成**: 未所属で近傍未所属数が `group_formation_neighbor_threshold` 以上かつ確率判定を通ると新グループ化し、拠点を記録。近傍未所属を少数リクルート。
- **採用/乗換**: 近傍多数派グループをスコアリング（`kin_bias` で同系譜に加点）。未所属は `group_adoption_neighbor_threshold` を満たすと確率で採用され、既所属は味方数が守衛閾値未満なら乗換許可。`sociality` で採用率を上げ、`loyalty` で乗換を抑制。小規模グループはボーナス係数で閾値を緩和。
- **孤立/離脱**: 所属中に至近味方がしきい値未満の時間が続くと乗換または未所属化。`loyalty` で猶予時間をスケールし、新規グループ生成は `founder` と確率で決定。
- **分裂**: 同グループ近傍が多くストレスが高いと `group_split_*` パラメータに基づき分裂。`founder` に応じて新グループ生成や近傍リクルートを行う。
- **拠点**: 形成・分裂・出生変異で拠点座標を記録。未所属は近傍拠点へ弱い吸引を受け、所属中は `group_base_attraction_weight` で緩やかに帰巣。存続しないグループの拠点は pruning。
- **出生時のグループ変異**: 親が未所属なら `group_birth_seed_chance`、所属中なら `group_mutation_chance` を `founder` 倍率付きで判定し、新グループを派生させる。

## 5. Steering と行動決定

`_compute_desired_velocity` が単位時間あたりの望ましい速度ベクトルを合成し、加速度・速度をクランプして積分する。バイアス源と優先度は以下の通り。

- **脅威回避**: 環境の危険フィールド勾配／他グループ至近距離（<2m）で即座に FLEE 状態となり、逃走ベクトルを返す。逃走または危険検知時は危険パルスを環境へペンディング。
- **食料探索**: 空腹またはセル食料が豊富なら食料勾配＋ワンダーを優先し `SEEKING_FOOD`。
- **繁殖探索**: エネルギー・年齢を満たすと近傍 Cohesion とフェロモン勾配を優先し `SEEKING_MATE`。
- **通常 Wander**: 定期リフレッシュされる `wander_dir` に jitter を掛けた遊泳。
- **局所バイアス**: `personal_space` 押し返し、同盟/異グループ Separation、`group_cohesion_radius` 内の Cohesion、Alignment（同盟速度平均）、未所属のグループ探索、拠点吸引、他グループ回避（`territoriality` で強調）、危険勾配の弱い押し返し。
- **境界処理**: マージン内で内向きバイアスとターン補正を掛け、最終的に反射境界で座標/速度を折り返し。重なりは `min_separation_distance` で位置補正。
- **記憶**: Steering を間引いた tick では前回の desired/danger 感知結果を再利用し、負荷分散と挙動一貫性を両立。

## 6. ライフサイクルとフィードバック

- **代謝とストレス**: 基礎代謝＋速度コストを trait スケールで減算し、高エネルギー超過分に追加代謝を課す。近傍密度に比例したストレス消耗。
- **過密ペナルティ**: `local_density_soft_cap` 超過でストレス蓄積と疾病確率上昇（`disease_resistance` で低減）。疾病死・エネルギー枯渇・寿命超過・確率ハザードで死亡した場合、食料を環境へ返還。
- **摂食**: そのセルの食料を `food_consumption_rate` まで消費しエネルギー獲得。
- **繁殖**: 初期人口が十分な場合のみ許可。エネルギー・年齢・人口上限を満たした個体が近傍からペアを選び、近傍密度と同盟人数で確率が減衰する。形質係数（`fertility`、`speed`、`disease_resistance`）は両親の幾何平均で反映し、成功すると両親がエネルギーを分担して子へ譲渡＋出産コスト支払い。
- **出生**: 子は親の中間地点近傍に生成。形質は両親平均に変異を加え、系譜は片親を継承し一定確率で新規化。所属グループは片親から 50/50 継承して変異ロジックを適用し、出生地点へフェロモンをペンディング。
- **ハザード**: 基礎＋年齢＋近傍密度に応じた確率死を毎 tick 判定。死亡・出生ともに後段で環境フィールドへ反映。

## 7. 環境フィールド

- **食料**: セルごとに最大量と再生量を持ち、`food_regen_noise_*` で決定論的に揺らす。`resource_patches` で高密度エリアを初期化。拡散・減衰は 4 近傍へ均等分配。
- **危険**: 逃走や脅威接近でパルス追加。拡散・減衰率は環境設定依存。`has_danger` を事前チェックして不要な勾配計算を避ける。
- **フェロモン**: グループ ID ごとのスカラー場。出生時にデポジットし、active なグループだけを残すよう `prune_pheromones` で層を整理。勾配はグループ Cohesion/探索に利用。
- **更新頻度**: `environment_tick_interval` ごとに食料再生→拡散、危険/フェロモン拡散・減衰、ノイズターゲット更新をバッチ処理し、Sim tick の負荷を平準化。

## 8. スナップショットとメトリクス

- **エージェントペイロード**: 位置/速度、heading、サイズ、エネルギー、年齢、行動状態、グループ、系譜 ID、世代、速度トレイトなどを JSON 化。`phase`/`is_alive` で死亡扱いを明示。
- **フィールド出力**: 食料セル一覧とフェロモン（セルごとに最優勢グループの値と ID）。危険フィールドは Phase 1 では送信しない。
- **メトリクス**: `TickMetrics` を `snapshot.metadata` と共に配信（`world_size`、`sim_dt`、`tick_rate`、`seed`）。Headless では basic/detailed CSV を切替でき、detailed ではストレスや群サイズ分布・セル占有状況・ストライド適用状況まで含められる。

## 9. View / インタラクション（`app/static/app.js`）

- **レンダリング**: 単一 `InstancedMesh` で全キューブを描画。scissor ビューポートで俯瞰・斜め・POV の 3 カメラを一度のフレームに収める。パフォーマンス維持のため影なし＋ピクセル比を 1.0〜1.3 に自動調整。
- **補間**: WebSocket スナップショットを Map 化し、前後位置/速度/heading/サイズを線形補間。1 体を自動選択して POV カメラを追従（消滅時は再選択）。
- **色/スケール**: 未所属は固定色 `#FFF2AA`（HSL 50°/100%/83%）で描画し、所属グループはこの基準色から `computeGroupHue` で色相を回転して決定する。エネルギー→明度、速度トレイト→彩度補正。成熟後は加齢で縮小し、繁殖欲求に応じたパルスで明滅＆スケール鼓動を与える。
- **UI**: tick/人口/POV 個体を表示。Start/Stop/Reset/Speed スライダは REST API を呼ぶだけで、Sim のタイミングを制御しない。接続バッジで WS 状態を表示し、切断時は自動再接続。

## 10. バリデーション手順（Phase 1）

- **必須テスト**: `pytest tests/python`。決定性、近傍取得、形質クランプ、環境ノイズの再現性、スナップショット内容、人口上限などをカバー。
- **長時間確認**: `python -m terrarium.app.headless --steps 5000 --seed 42 --log tests/artifacts/metrics.csv --log-format detailed --summary tests/artifacts/summary.json` で headless 実行し、ピーク人口・tick 時間・近傍チェックなどが安定していることを確認。
- **表示確認**: `uvicorn terrarium.app.server:app --reload --port 8000` を起動し、ブラウザでスナップショットが補間表示されることを目視。Sim を止めても View がスムーズに補間/再接続することを確認する。

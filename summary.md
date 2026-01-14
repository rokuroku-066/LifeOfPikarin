# .agent/plans 実行計画の時系列サマリー（作成タイムスタンプ基準）

本ドキュメントは `.agent/plans` 配下（アーカイブ含む）の ExecPlan を全件確認し、**各ファイルの「作成タイムスタンプ（git での初回追加時刻）」を基準**に時系列で整理したものです。ファイルシステムの birthtime が取得できないため、`git log --diff-filter=A` の初回コミット時刻を「作成時刻」として採用しています。ExecPlan 内に記載された日付と並びが一致しない場合があることを前提に、**タイムラインは作成タイムスタンプ順**で記述しています。

## 2025-12-10

### ExecPlan: Build simulation and visualization codebase matching docs/DESIGN.md (`full_implementation_execplan.md`)
- 目的: Sim/View 分離・決定性・SpatialGrid 局所性・負のフィードバックを満たす Phase 1 のフル実装計画（Sim/Core・Unity View・テスト・ヘッドレス・メトリクス）を策定
- 改修内容: Sim/View 分離・決定性・SpatialGrid 局所性・負のフィードバックを満たす Phase 1 のフル実装計画（Sim/Core・Unity View・テスト・ヘッドレス・メトリクス）を策定。
- 課題と解決: 課題: dotnet SDK 不在でのテスト実行と、TickDuration の非決定性。 / 解決: SDK 導入後に `dotnet test` を実行し、TickDuration を決定性比較から除外して再現性を担保。

### Environment resource patches and fields (`environment_fields_execplan.md`)
- 目的: 資源パッチ、hazard/pheromone フィールド、regen/diffuse/decay を導入し環境を拡張
- 改修内容: 資源パッチ、hazard/pheromone フィールド、regen/diffuse/decay を導入し環境を拡張。
- 課題と解決: 課題: 初期環境で dotnet SDK 不在によりテストが走らない。 / 解決: 後日 Windows 環境で .NET 8.416 によりテスト通過を確認。

### C#9 compatibility refactor for Unity 6 (`csharp9_compat_execplan.md`)
- 目的: file-scoped namespace/record/init を C#9 互換構文に置換し Unity 6 対応
- 改修内容: file-scoped namespace/record/init を C#9 互換構文に置換し Unity 6 対応。
- 課題と解決: 課題: dotnet CLI 不在。 / 解決: Windows 環境で .NET 8.416 テストを実行し互換性を確認。

### Environment field diffusion and decay integration (`environment_field_diffusion_execplan.md`)
- 目的: food/pheromone/danger の拡散・減衰と AI への統合
- 改修内容: food/pheromone/danger の拡散・減衰と AI への統合。
- 課題と解決: 課題: danger 勾配が無い場合の逃避が不安定。 / 解決: 勾配不在時のランダム逃避ベクトルを追加。

### Population Stability & Throughput Improvements (`population_stability_execplan.md`)
- 目的: 早期出生の促進、密度・年齢・エネルギーによる死亡/繁殖調整、初期年齢のランダム化
- 改修内容: 早期出生の促進、密度・年齢・エネルギーによる死亡/繁殖調整、初期年齢のランダム化。
- 課題と解決: 課題: PowerShell で Sim.dll を Add-Type できず smoke run 失敗。 / 解決: dotnet run の headless runner を使用してメトリクス取得。

### Remaining task sweep (`remaining_tasks_execplan.md`)
- 目的: テスト実行の追跡、Unity DTO 既定値同期、headless smoke run の整理
- 改修内容: テスト実行の追跡、Unity DTO 既定値同期、headless smoke run の整理。
- 課題と解決: 課題: TickDuration の決定性比較が破綻。 / 解決: TickDuration を比較対象から外し、テストを再実行。

## 2025-12-11

### Group Formation From Zero With Rare Merge/Split (`group_formation_dynamics_execplan.md`)
- 目的: GroupId=-1 の「ゼロスタート」導入と低頻度の merge/split を追加
- 改修内容: GroupId=-1 の「ゼロスタート」導入と低頻度の merge/split を追加。
- 課題と解決: 課題: 群れ形成の視認性と決定性維持。 / 解決: warmup と局所確率により形成を制御し、Sim/View 分離と決定性を保持。

## 2025-12-12

### ブラウザ向けPython実装への移行計画 (`browser_python_web_execplan.md`)
- 目的: C# から Python 実装へ移行する計画を詳細化（FastAPI + WebSocket + Web 可視化）
- 改修内容: C# から Python 実装へ移行する計画を詳細化（FastAPI + WebSocket + Web 可視化）。
- 課題と解決: 課題: dotnet 不在で C# テストが実行不能。 / 解決: Python テストで決定性確認を行い、C# 側は後日検証方針に。

### Remove legacy C# implementation and references (`remove_csharp_cleanup_execplan.md`)
- 目的: C#/Unity ソース撤去と Python-only への整理
- 改修内容: C#/Unity ソース撤去と Python-only への整理。
- 課題と解決: 課題: ドキュメント・依存・ツールの整理が必要。 / 解決: README 更新と pytest 実行で整合性を確保。

### Web viewer to Three.js instanced renderer (`three_js_renderer_execplan.md`)
- 目的: 2D Canvas を Three.js InstancedMesh に置換
- 改修内容: 2D Canvas を Three.js InstancedMesh に置換。
- 課題と解決: 課題: レンダリング移行後の検証。 / 解決: pytest 実行と手動視覚確認を明記。

### Replace custom Vec2 with pygame.math.Vector2 (`pygame_vector_execplan.md`)
- 目的: Vec2 を pygame Vector2 に置換、normalize/clamp を安全化
- 改修内容: Vec2 を pygame Vector2 に置換、normalize/clamp を安全化。
- 課題と解決: 課題: pygame 依存追加が必要。 / 解決: requirements 導入と pytest で検証。

### Add JavaScript unit tests for viewer utilities (`add-js-tests.md`)
- 目的: `computeGroupHue` を切り出し Node の組み込みテストを追加
- 改修内容: `computeGroupHue` を切り出し Node の組み込みテストを追加。
- 課題と解決: 課題: JS テスト基盤が未整備。 / 解決: Node の標準テストランナーを採用し、依存を増やさずテストを整備。

### Perspective camera, lighting, and interpolation update (`perspective_camera_interpolation_execplan.md`)
- 目的: 斜め視点カメラ、ライティング/シャドウ、速度ベースの補間描画を導入
- 改修内容: 斜め視点カメラ、ライティング/シャドウ、速度ベースの補間描画を導入。
- 課題と解決: 課題: 依存導入時に pygame が必要。 / 解決: pytest 実行時に dependencies を導入。

### Group cohesion hysteresis and switching (`group_cohesion_detach_execplan.md`)
- 目的: group_lonely_seconds によるヒステリシス、スイッチング閾値を導入
- 改修内容: group_lonely_seconds によるヒステリシス、スイッチング閾値を導入。
- 課題と解決: 課題: 多数派判定の安定性。 / 解決: 近傍閾値を追加し deterministic テストで担保。

### Replace periodic boundaries with reflective bounce behavior (`2025-12-12-boundary-reflect.md`)
- 目的: periodic boundary を反射境界に変更
- 改修内容: periodic boundary を反射境界に変更。
- 課題と解決: 課題: headless 実行に PYTHONPATH が必要。 / 解決: PYTHONPATH=src の設定を明記。

### Phase 2 snapshot signals and metadata prework (`phase2-snapshot-signals.md`)
- 目的: heading/状態/メタデータ追加で Phase 2 の信号拡充
- 改修内容: heading/状態/メタデータ追加で Phase 2 の信号拡充。
- 課題と解決: 課題: Sim ループ非干渉を維持。 / 解決: スナップショットのみ拡張し Sim/View 分離を保持。

### Multi-view cameras for web viewer (`multi_view_cameras_execplan.md`)
- 目的: top/angle/POV の 3 分割カメラ表示を導入
- 改修内容: top/angle/POV の 3 分割カメラ表示を導入。
- 課題と解決: 課題: JS テストの glob パス問題。 / 解決: `node --test` のパス指定を明示。

## 2025-12-13

### Boundary Avoidance Steering (`boundary_avoidance_execplan.md`)
- 目的: 壁面への滞留を軽減する soft boundary avoidance を追加
- 改修内容: 壁面への滞留を軽減する soft boundary avoidance を追加。
- 課題と解決: 課題: テスト時の reproduction 干渉や OOB グリッド。 / 解決: テスト用の config 制御と grid key クランプで対応。

### Intra-group Clustering and Inter-group Spacing (`group_clustering_execplan.md`)
- 目的: 同色結束強化と異色分離を追加し、群れの可視性を向上
- 改修内容: 同色結束強化と異色分離を追加し、群れの可視性を向上。
- 課題と解決: 課題: 過度な bias で群れ形成が弱くなる可能性。 / 解決: weight を調整して安定と見た目を両立。

### Clamp diffusion fields and keep pheromones finite (`perf_pheromone_clamp_execplan.md`)
- 目的: pheromone key の無限増殖を抑制する clamp/decay/prune を導入
- 改修内容: pheromone key の無限増殖を抑制する clamp/decay/prune を導入。
- 課題と解決: 課題: tick_ms の上昇と config ファイルの破損。 / 解決: clamp + decay + group prune、config を UTF-8 で再構築。

### Cube appearance cues for Phase 1 viewer (`cube_phase1_appearance_execplan.md`)
- 目的: energy/age/repro の視覚表現（明度/スケール/パルス）を追加
- 改修内容: energy/age/repro の視覚表現（明度/スケール/パルス）を追加。
- 課題と解決: 課題: pygame 未導入で pytest が失敗。 / 解決: .venv 環境で deps 導入しテスト通過。

### Reduce sim/render stutter (`2025-12-13-perf_smooth_execplan.md`)
- 目的: environment tick 間隔や視野距離の調整で tick_ms を削減
- 改修内容: environment tick 間隔や視野距離の調整で tick_ms を削減。
- 課題と解決: 課題: 拡散が毎 tick 実行で重い。 / 解決: env tick cadence を導入して負荷を平準化。

### Density Penalty Softening (`density_penalty_soften_execplan.md`)
- 目的: 密度ペナルティを緩和し群れの密集を許容
- 改修内容: 密度ペナルティを緩和し群れの密集を許容。
- 課題と解決: 課題: 過密で安定性が崩れる懸念。 / 解決: 疾病/ストレス/繁殖抑制のバランスを調整して維持。

### Wide-Spread Group Split to New Colony (`group_wide_split_execplan.md`)
- 目的: 孤立個体が新群を形成する分裂パスを追加
- 改修内容: 孤立個体が新群を形成する分裂パスを追加。
- 課題と解決: 課題: 過剰分裂の可能性。 / 解決: 確率パラメータを追加し、テストで挙動を固定。

## 2025-12-14

### Size-Scaled Group Splitting (`2025-12-13-group_size_split_scaling.md`)
- 目的: 群サイズに比例した split 確率、merge cooldown、minority guard を導入
- 改修内容: 群サイズに比例した split 確率、merge cooldown、minority guard を導入。
- 課題と解決: 課題: 5k tick で群れが一極化。 / 解決: 追加ガードにより 12k tick で多数群を維持。

### Phase 1 ExecPlan Summary (`phase1_summary.md`)
- 目的: Phase 1 の ExecPlan を時系列で総括
- 改修内容: Phase 1 の ExecPlan を時系列で総括。
- 課題と解決: 課題: 長期パフォーマンス検証の整理が必要。 / 解決: smoke run の結果と課題を整理して記載。

### Small groups recruit nearby agents more easily (`2025-12-14-group_adoption_small_groups_execplan.md`)
- 目的: 小規模群が近傍を取り込みやすい採用率を導入
- 改修内容: 小規模群が近傍を取り込みやすい採用率を導入。
- 課題と解決: 課題: 群れ形成のバランス。 / 解決: パラメータ調整と pytest で検証。

### Smooth step performance pass (`2025-12-14-performance_smoothing_execplan.md`)
- 目的: per-tick の余分なループ/alloc を削減
- 改修内容: per-tick の余分なループ/alloc を削減。
- 課題と解決: 課題: 実行環境の Python バージョンが 3.9.7。 / 解決: 3.9.7 環境でも pytest を通し互換性を確認。

### Spatial neighbor perf (`2025-12-14-spatial_neighbor_perf_execplan.md`)
- 目的: SpatialGrid の参照再利用と近傍処理の最適化
- 改修内容: SpatialGrid の参照再利用と近傍処理の最適化。
- 課題と解決: 課題: headless 実行時の PYTHONPATH 問題。 / 解決: PYTHONPATH=src を明記。

### Tick duration control (`2025-12-14-tick_duration_control_execplan.md`)
- 目的: 10k tick で tick_ms を 2–6ms に抑える config tuning
- 改修内容: 10k tick で tick_ms を 2–6ms に抑える config tuning。
- 課題と解決: 課題: 初期設定で tick_ms が 60–110ms に上昇。 / 解決: cell size や food/metabolism を調整して安定化。

### Randomly fluctuate food regeneration (`2025-12-14-food_regen_noise_execplan.md`)
- 目的: deterministic climate noise による food regen 変動
- 改修内容: deterministic climate noise による food regen 変動。
- 課題と解決: 課題: headless 実行で ModuleNotFoundError。 / 解決: PYTHONPATH=src を設定して実行。

### Group base attraction + no-overlap separation (`2025-12-14-group_base_attraction_execplan.md`)
- 目的: group の base anchor と近距離 repulsion 強化
- 改修内容: group の base anchor と近距離 repulsion 強化。
- 課題と解決: 課題: headless CSV の tick_ms が非決定。 / 解決: deterministic log か tick_ms 列の無視を前提化。

### Remove group-food spawning knobs and mechanic (`2025-12-14-remove_group_food_spawn_execplan.md`)
- 目的: group-only food の spawn/mechanic を完全撤去
- 改修内容: group-only food の spawn/mechanic を完全撤去。
- 課題と解決: 課題: 削除範囲が広く、参照の残存が懸念。 / 解決: rg 検索で参照を削除し pytest で検証。

### Remove danger field system (`2025-12-14-remove_danger_field_execplan.md`)
- 目的: danger フィールドの config/保存/拡散/ステアを完全撤去
- 改修内容: danger フィールドの config/保存/拡散/ステアを完全撤去。
- 課題と解決: 課題: 関連テスト・ドキュメント更新が必要。 / 解決: pytest と headless smoke run で整合を確認。

## 2025-12-15

### Overlay of Environment Fields for Viewer (`2024-05-21-env_fields_overlay_execplan.md`)
- 目的: food/pheromone の疎データをスナップショットに載せ、View にオーバーレイ表示
- 改修内容: food/pheromone の疎データをスナップショットに載せ、View にオーバーレイ表示。
- 課題と解決: 課題: payload サイズ増と帯域負荷。 / 解決: pheromone をセル単位の最大濃度に集約。

### Achieve 5000-tick performance and stability targets (`2025-12-15-performance_targets_5000tick_execplan.md`)
- 目的: 5k tick の性能/安定性テストを追加し、パラメータを調整
- 改修内容: 5k tick の性能/安定性テストを追加し、パラメータを調整。
- 課題と解決: 課題: tick_ms と group 数が上限を超過。 / 解決: formation/split を段階的に調整し、cap を導入。

### Reduce unaffiliated individuals (`reduce_unaffiliated.md`)
- 目的: ungrouped の加入バイアスと群間スペースを調整
- 改修内容: ungrouped の加入バイアスと群間スペースを調整。
- 課題と解決: 課題: 長期テストで ungrouped 割合が高い。 / 解決: 5k tick のアサーション追加とパラメータ調整。

### Speed up long-run terrarium test (`2025-12-15-long_run_performance_execplan.md`)
- 目的: 5000 tick 長期テストを高速化し、群れ安定を維持
- 改修内容: 5000 tick 長期テストを高速化し、群れ安定を維持。
- 課題と解決: 課題: 既存設定では 5000 tick がタイムアウト。 / 解決: env tick cadence と初期スキップで wall time を短縮。

## 2025-12-16

### Remove abrupt population capping (`remove_population_cap.md`)
- 目的: hard cap を廃止し連続的フィードバックに移行
- 改修内容: hard cap を廃止し連続的フィードバックに移行。
- 課題と解決: 課題: global population pressure の調整が難しい。 / 解決: start/slope/delay を調整しピークを制御。

### Remove bootstrap_mode configuration (`remove_bootstrap_mode.md`)
- 目的: bootstrap_mode を削除し最初から近傍/ステアを有効化
- 改修内容: bootstrap_mode を削除し最初から近傍/ステアを有効化。
- 課題と解決: 課題: long_run テストへの影響。 / 解決: テスト更新と pytest 実行で確認。

### Strengthen agent collision avoidance (`strengthen_collision_avoidance.md`)
- 目的: separation と overlap 補正を強化
- 改修内容: separation と overlap 補正を強化。
- 課題と解決: 課題: ステアだけでは距離が確保できない。 / 解決: 位置補正の併用で最小距離を改善。

## 2025-12-17

### Introduce deterministic lineage traits and evolution hooks (`evolution_traits_lineage.md`)
- 目的: lineage/traits を導入し、進化トレイトを決定的に付与
- 改修内容: lineage/traits を導入し、進化トレイトを決定的に付与。
- 課題と解決: 課題: 既存挙動の維持と RNG 消費の制御。 / 解決: evolution 無効時は RNG を追加消費しない方針に。

## 2025-12-18

### Food-limited population waves (`2025-12-18-population_waves_execplan.md`)
- 目的: global population pressure を廃止し food scarcity で波形制御
- 改修内容: global population pressure を廃止し food scarcity で波形制御。
- 課題と解決: 課題: free energy が残ると暴走。 / 解決: group-food spawning を除去しバランス調整。

### Spatial grid and environment hotpath allocation cuts (`2025-05-10-performance_spatial_environment_execplan.md`)
- 目的: SpatialGrid/Environment の alloc 削減と neighbor distance 再利用
- 改修内容: SpatialGrid/Environment の alloc 削減と neighbor distance 再利用。
- 課題と解決: 課題: 既存 API の互換性。 / 解決: optional 引数で後方互換を維持。

## 2025-12-19

### Add social/territorial lineage traits (`social_traits_factions.md`)
- 目的: social/territorial traits を追加し group 行動にバイアスを付与
- 改修内容: social/territorial traits を追加し group 行動にバイアスを付与。
- 課題と解決: 課題: 長期の視覚/安定性チェックが未完了。 / 解決: pytest で決定性確認し、長期観測はフォローアップ。

### Remove group food spawn and global population pressure (`remove_group_food_spawn_population_pressure.md`)
- 目的: group_food_spawn と global population pressure を削除
- 改修内容: group_food_spawn と global population pressure を削除。
- 課題と解決: 課題: config の整理が必要。 / 解決: 関連 field を削除し pytest を再実行。

### Remove explicit group cap config fields (`remove_group_cap_config_fields.md`)
- 目的: max_groups などの cap を削除
- 改修内容: max_groups などの cap を削除。
- 課題と解決: 課題: doc/test の整合。 / 解決: 参照削除と pytest で確認。

### Neighbor distance buffers in SpatialGrid (`neighbor-distance-buffers.md`)
- 目的: neighbor dist^2 バッファを導入して再計算を削減
- 改修内容: neighbor dist^2 バッファを導入して再計算を削減。
- 課題と解決: 課題: 0 近傍時のクリア漏れ。 / 解決: テストでバッファクリアを保証。

### Gradient sampling via grid keys (`gradient-neighbor-keys.md`)
- 目的: gradient 計算を grid key 化し Vector2 alloc を削減
- 改修内容: gradient 計算を grid key 化し Vector2 alloc を削減。
- 課題と解決: 課題: 結果の一致保証。 / 解決: 固定シナリオテストで一致を検証。

## 2025-12-20

### Reduce tick_ms under 20ms (`2025-12-19-tick_ms_execplan.md`)
- 目的: group update の time-slice 化と alloc 削減で 20ms 未満を目標化
- 改修内容: group update の time-slice 化と alloc 削減で 20ms 未満を目標化。
- 課題と解決: 課題: neighbor aggregation を単一パス化すると逆効果。 / 解決: 集約は撤回し軽量最適化に切替。

### Aggregate neighbor steering calculations (`2025-12-20-neighbor_bias_aggregation_execplan.md`)
- 目的: 近傍処理の単一パス集約を試行
- 改修内容: 近傍処理の単一パス集約を試行。
- 課題と解決: 課題: 平均 tick_ms が悪化。 / 解決: 集約を撤回し、別の軽量最適化で改善。

### Enhance headless smoke run logging (`2025-12-20-smoke_run_metrics_execplan.md`)
- 目的: headless の詳細 CSV/JSON ログ出力を追加
- 改修内容: headless の詳細 CSV/JSON ログ出力を追加。
- 課題と解決: 課題: 既存テストとの整合。 / 解決: log format オプションとテスト更新で対応。

### Time-sliced steering updates (`2025-12-20-steering_stride_execplan.md`)
- 目的: steering を stride 更新化し tick_ms を削減
- 改修内容: steering を stride 更新化し tick_ms を削減。
- 課題と解決: 課題: stride 導入で人口ピークが上昇。 / 解決: 回帰テストとパラメータ調整で抑制。

## 2025-12-24

### World step performance optimizations (`world-step-performance.md`)
- 目的: Vector2 の in-place 更新、scratch buffer 再利用、事前計算の導入
- 改修内容: Vector2 の in-place 更新、scratch buffer 再利用、事前計算の導入。
- 課題と解決: 課題: 共有 Vector2 の副作用でテスト破綻。 / 解決: テスト側で初期座標をスナップショット化。

## 2025-12-25

### Refactor terrarium package layout (`terrarium-structure-refactor.md`)
- 目的: `app/` と `sim/` の分割、world.py を systems/types/utils に分割
- 改修内容: `app/` と `sim/` の分割、world.py を systems/types/utils に分割。
- 課題と解決: 課題: import 変更と packaging metadata 更新。 / 解決: pyproject の packages 設定を更新しテストで確認。

### Phase 2 viewer refresh (`phase2-viewer.md`)
- 目的: 単一固定カメラ、GLB instancing、床/壁の diorama を導入
- 改修内容: 単一固定カメラ、GLB instancing、床/壁の diorama を導入。
- 課題と解決: 課題: GLB が空の場合に描画が破綻。 / 解決: フォールバック geometry と placeholder 生成スクリプトを整備。

### Fix viewer base color (`ungrouped-color-base.md`)
- 目的: ungrouped の基準色を #FFF2AA に固定し、group hue を回転
- 改修内容: ungrouped の基準色を #FFF2AA に固定し、group hue を回転。
- 課題と解決: 課題: JS テストの glob 展開が失敗。 / 解決: `node --test` をファイル単位で実行。

### Add per-agent genetic appearance colors (`appearance-genetics.md`)
- 目的: appearance HSL を遺伝値として導入し View で色適用
- 改修内容: appearance HSL を遺伝値として導入し View で色適用。
- 課題と解決: 課題: RNG 消費順の維持。 / 解決: appearance 専用 RNG を導入し影響を分離。

### Implement pair-based reproduction (`pair-reproduction.md`)
- 目的: 近傍ペア繁殖へ移行し、両親継承ロジックを追加
- 改修内容: 近傍ペア繁殖へ移行し、両親継承ロジックを追加。
- 課題と解決: 課題: ペア選択の決定性。 / 解決: 最近傍 + ID でタイブレーク。

## 2025-12-26

### Add deterministic trait RNG stream (`deterministic-trait-rng.md`)
- 目的: bootstrap traits 専用 RNG を導入し決定性を維持
- 改修内容: bootstrap traits 専用 RNG を導入し決定性を維持。
- 課題と解決: 課題: メイン RNG 消費の変化を避ける必要。 / 解決: 専用 RNG によるサンプリングで隔離。

### Refactor World.step orchestration (`world-step-refactor.md`)
- 目的: World.step を helper に分解し可読性を向上
- 改修内容: World.step を helper に分解し可読性を向上。
- 課題と解決: 課題: RNG/neighbor buffer の順序維持。 / 解決: 同一ファイル内 helper で順序を固定。

### Add group-biased hue mutation (`appearance-group-bias.md`)
- 目的: group_id による hue バイアスを導入
- 改修内容: group_id による hue バイアスを導入。
- 課題と解決: 課題: pair reproduction で child group 選択が必要。 / 解決: child group id を基準に bias を適用。

## 2026-01-05

### Blend ally cohesion/alignment during flee (`flee-cohesion-alignment.md`)
- 目的: flee 中も ally cohesion/alignment を維持
- 改修内容: flee 中も ally cohesion/alignment を維持。
- 課題と解決: 課題: flee が早期 return していた。 / 解決: flee ベクトルに ally 項をブレンド。

## 2026-01-14

### Compile .agent/plans history into summary.md (`summary-md-execplan.md`)
- 目的: 本 summary.md の作成と ExecPlan のアーカイブ計画を策定
- 改修内容: 本 summary.md の作成と ExecPlan のアーカイブ計画を策定。
- 課題と解決: 課題: ExecPlan 内の日付は誤りがあるため、作成タイムスタンプを基準に並べる必要。 / 解決: git 初回追加時刻を基準にタイムラインを再構成。


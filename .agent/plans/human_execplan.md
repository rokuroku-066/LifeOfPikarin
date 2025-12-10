# 人間が実施する皇族作業用ExecPlan: Unity視覚検証と長時間運用確認

このExecPlanは生きたドキュメントです。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective` の各セクションを作業の進捗に合わせて更新してください。

本ドキュメントはリポジトリルートの `.agent/PLANS.md` に従って維持してください。

## Purpose / Big Picture

Unity 上で Phase 1 (キューブ描画) の長時間シミュレーションを人手で検証し、設計ドキュメント通りに視覚挙動・安定性・性能が満たされていることを確認する。結果として、第三者が同じ手順で Unity プロジェクトをセットアップし、頭上カメラ視点で複数コロニーが形成・維持されることを観察できる状態を目指す。

## Progress

作業停止・再開時はチェックボックスと UTC タイムスタンプで更新すること。
- [ ] (YYYY-MM-DD HH:MMZ) Unity プロジェクトに `src/Sim`/`src/Unity` を導入し、インスタンシング描画が動作することを確認。
- [ ] (YYYY-MM-DD HH:MMZ) Unity 上で定常ラン (≥20,000 ticks 相当) を行い、人口が飽和も壊滅もしないことを観察。
- [ ] (YYYY-MM-DD HH:MMZ) 1k/5k/10k エージェントのパフォーマンス計測を実施し、 tick 時間と NeighborChecks を記録。
- [ ] (YYYY-MM-DD HH:MMZ) データ・スクリーンショット・CSV を成果物として保存し、パスを記録。

## Surprises & Discoveries

予想外の挙動やボトルネックを記録する。再現手順やログの短い抜粋を添えること。

## Decision Log

- Decision: 
  Rationale: 
  Date/Author: 

## Outcomes & Retrospective

完了時に結果と今後の改善点をまとめる。目的に照らして評価すること。

## Context and Orientation

- 設計の要件は `docs/DESIGN.md` にある。特に Sim/View 分離、SpatialGrid による近傍限定、負のフィードバックによる長期安定性、決定論的シード運用を厳守する。
- 現状のヘッドレス実行は `src/SimRunner` と `src/Sim/HeadlessRunner.cs` で提供され、CSV を出力する。Unity 側レンダラーは未実装で、手動作業が必要。
- テストやヘッドレス計測に使う構成例は `tests/SimTests/WorldTests.cs` にある。NeighborChecks や人口上限の振る舞いを理解する参考にする。

## Plan of Work

1. Unity プロジェクトを新規作成し、`src/Sim` をアセンブリ定義としてインポート、`src/Unity` のビュー層スクリプトを配置する。RenderPipeline はデフォルト (URP/HDRP いずれでも可) とし、GPU instancing が有効なマテリアルを用意する。
2. シーンに固定タイムステップのホスト MonoBehaviour を追加し、`World` をシード付きで生成して `AgentViewMapper` (必要なら新規作成) にスナップショットを供給する。描画は `Graphics.DrawMeshInstancedIndirect` か `Graphics.DrawMeshInstanced` でキューブを GPU インスタンス描画する。
3. 頭上カメラを設定し、人口が多い領域を俯瞰できるようにする。Gizmos/デバッグ表示で SpatialGrid セル境界やコロニー色分けを確認できるようにする。
4. 長時間ランのために自動ロギングを準備する。各 tick (または数 tick に 1 回) で `World.Metrics` を CSV/JSON に追記し、Unity 側でもフレーム時間と描画コール回数を記録する。
5. 定常ラン観察: 20,000 tick 相当の時間を走らせ、人口・出生・死亡・NeighborChecks が上下動しつつ上限内で安定すること、複数の色付きコロニーが分離/合流を繰り返しながら維持されることを確認する。
6. パフォーマンス計測: 1k/5k/10k エージェントで固定パラメータを用意し、Editor とビルド後 (可能なら) の平均 tick 時間、フレーム時間、NeighborChecks を記録。メモリ使用量と GC 発生の有無も観察する。
7. 収集した CSV・スクリーンショットを `artifacts/` 配下などに整理し、再現に必要なシード・設定ファイル・Unity バージョンを明記する。

## Concrete Steps

- (Unity) 新規 3D プロジェクトを作成し、`Assets/Sim` に `src/Sim` のコードをコピーして asmdef を作成。`Assets/UnityView` にビュー用スクリプトを配置し、Sim への参照を asmdef で追加する。
- (Unity) マテリアルで GPU Instancing を有効化したキューブ Mesh を用意し、レンダラースクリプトに設定する。
- (Unity) `World` のコンストラクタに渡す `SimulationConfig` を ScriptableObject で管理し、シード・人口上限・フィードバック設定を編集できるインスペクタを用意する。
- (Unity) 再生後に自動で長時間ランを続けるため、`Application.runInBackground = true` を設定し、ログ出力先を `Application.persistentDataPath` 配下に作る。
- (Headless確認) `.NET 8 SDK` をインストールし、リポジトリルートで `dotnet test tests/SimTests/SimTests.csproj` および `dotnet run --project src/SimRunner/SimRunner.csproj -- --steps 5000 --seed 123 --log artifacts/metrics.csv` を実行して CSV を生成。Unity 側の結果と傾向が一致するか比較する。

## Validation and Acceptance

- 決定論的スモーク: `dotnet run --project src/SimRunner/SimRunner.csproj -- --steps 2000 --seed 42 --log artifacts/metrics.csv` を 2 回実行し、CSV が一致すること (TickDurationMs の微差は許容)。
- 長期安定性: Unity で 20,000 tick 相当を実行し、人口が 0 にならず `MaxPopulation` を超えないこと、出生/死亡が周期的に発生することを確認。ストレス/疾病ペナルティが高密度域で発火し、群れが分散する様子を観察する。
- パフォーマンス: 1k/5k/10k エージェントの平均 tick 時間を測定し、目安として ≤0.5ms/≤3ms/≤7ms (リファレンス環境) に収まることを目標とする。NeighborChecks が局所密度に比例し、全体人口に比例しないことをログで確認する。
- Sim/View 分離: View 側は `World` の状態を読み取るのみで、Simulation ループは固定タイムステップで独立に進むことをコードレビューで確認する。
- No O(N²): SpatialGrid への挿入/更新/除去と 3×3 近傍クエリのみを使い、全エージェント走査がないことを確認する。
- 視覚: 頭上カメラで複数のコロニー色が識別でき、過密時に色の混在が解消される動きが見えること。スクリーンショットを保存する。

## Idempotence and Recovery

- Unity プロジェクトのライブラリが壊れた場合は `Library/` を削除して再インポートする。設定 ScriptableObject はバージョン管理する。
- ログ/CSV 出力先は毎回新しいファイル名にして上書き衝突を防ぐ。再実行で同じシードを使えば決定論的に再現できる。

## Artifacts and Notes

- `artifacts/metrics-<seed>-<steps>.csv`: ヘッドレス/Unity でのメトリクス出力。
- `artifacts/screenshots/`: コロニー形成・過密分散のスクリーンショット。
- パフォーマンス計測の表やコメントをここに追記すること。

## Interfaces and Dependencies

- 依存: .NET 8 SDK (ヘッドレス確認用)、Unity 2022+ (URP/HDRP いずれか)、GPU instancing が有効なシェーダ。
- インターフェース: `Terrarium.Sim.World` (fixed-step 更新), `SimulationConfig` (Seed/InitialPopulation/MaxPopulation/Feedback 設定), `HeadlessRunner` (CSV 出力), Unity 側の `AgentViewMapper`/レンダラー (Sim state を ComputeBuffer/NativeArray に投影し描画)。
- 最終的に、Sim 側のデータ構造や SpatialGrid への依存を崩さずに View を接続すること。

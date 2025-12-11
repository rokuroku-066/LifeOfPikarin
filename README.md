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

- **Simulation**: `src/Sim/` にエンジン非依存の C# コア
- **Visualization**: Unity 側の表示レイヤーは `src/Unity/` のマッピングコードをベースに、キューブを GPU インスタンシングで描画する想定
- **Headless 実行**: `src/SimRunner/` のコンソールアプリでシミュレーションをステップ実行し、CSV でメトリクスを出力可能
- **テスト**: `tests/SimTests/` に決定性・フィードバック・グリッド近傍検索などのユニットテスト

---

## 開発環境

| 目的 | 推奨ツール | 備考 |
| --- | --- | --- |
| Unity での表示 | **Unity 6.3 LTS**（6.x LTS 系列推奨） | Unity Hub からインストールし、このリポジトリを開く |
| シミュレーション実行・テスト | **.NET 8 SDK** | `dotnet --info` で 8 系が見えることを確認 |
| バージョン管理 | Git | 任意のクライアントで OK |

> `.NET 8 SDK` のインストール手順は `AGENTS.md` にも記載があります。環境に合わせてセットアップしてください。

---

## ディレクトリ構成

```text
.
├── AGENTS.md             # Codex 向けガイド
├── .agent/PLANS.md       # ExecPlan の運用ルール
├── docs/DESIGN.md        # システム設計（Simulation / View / Grid 等）
├── src/
│   ├── Sim/              # シミュレーションコア（エンジン非依存 C#）
│   ├── SimRunner/        # ヘッドレス実行用コンソールアプリ
│   └── Unity/            # Unity 統合層・表示マッピングなど
├── tests/SimTests/       # シミュレーションのユニットテスト
└── Terrarium.sln         # .NET ソリューション
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone https://github.com/rokuroku-066/LifeOfPikarin.git
   cd LifeOfPikarin
   ```
2. .NET SDK をインストールし、`dotnet --info` で 8.x が利用できることを確認。
3. Unity 6.x LTS を Unity Hub からインストールし、プロジェクトを開く。
   - Windows では `setup_windows_env.bat` をルートで実行すると、.NET 8 SDK の導入確認と Unity Hub / Unity 6.x LTS の有無チェック、ソリューション復元、テスト実行までまとめて行えます。

---

## シミュレーションの実行（ヘッドレス）

`src/SimRunner/` のコンソールアプリでステップ単位のシミュレーションを回し、CSV にメトリクスを書き出します。

```bash
dotnet run --project src/SimRunner/SimRunner.csproj \
  -- --steps 3000 --seed 42 \
  --initial 120 --max 500 \
  --log artifacts/metrics_smoke.csv
```

出力される CSV のカラム例:

- `tick`: シミュレーションステップ
- `population`: 生存個体数
- `births` / `deaths`: ステップ中の出生・死亡数
- `avgEnergy` / `avgAge`: 平均エネルギー・平均年齢
- `groups`: グループ（群れ）数（初期は 0。未所属の個体はカウントしない）
- `neighborChecks`: 近傍判定のカウント（O(N^2) を避けるためのヘルス指標）
- `tickDurationMs`: 1 ステップの処理時間（ミリ秒）

`--log` で指定したパス配下にディレクトリが無ければ自動で作成されます。主要な調整パラメータ（`SimulationConfig` と Unity インスペクタの DTO は同じ項目を持ちます）:
- エネルギー上限と代謝: `EnergySoftCap`, `HighEnergyMetabolismSlope`, `MetabolismPerSecond`, `InitialEnergyFractionOfThreshold`
- 繁殖トリガ: `ReproductionEnergyThreshold`, `AdultAge`, `DensityReproductionSlope`, `DensityReproductionPenalty`
- 寿命/危険: `BaseDeathProbabilityPerSecond`, `AgeDeathProbabilityPerSecond`, `DensityDeathProbabilityPerNeighborPerSecond`
- 環境フィールド: `FoodRegenPerSecond`, `FoodFromDeath`, `DangerDiffusionRate` / `DangerDecayRate`, `PheromoneDepositOnBirth`
- グループ形成・分離: `GroupFormationWarmupSeconds`, `GroupFormationChance`, `GroupAdoptionChance`, `GroupSplitChance` など（初期グループ数は 0）

---

## テスト

シミュレーションコアの決定性や安定性はユニットテストで確認できます。

```bash
dotnet test tests/SimTests/SimTests.csproj
```

- 固定シードでの結果一致、近傍検索の範囲制限、負のフィードバックによる個体数抑制、メトリクス CSV 出力などをカバーしています。

### 環境フィールド

`EnvironmentGrid` はセル毎に `food`・`pheromone`（グループ別）・`danger` の 3 スカラーフィールドを持ち、毎ステップで減衰と隣接セルへの拡散を行います。

- `food`: パッチ定義で初期化され、時間経過で再生・拡散し、消費や死亡で追加されます。`World.Step` の Forage 行動は `food` 勾配を優先。
- `pheromone`: 繁殖成功地点で自グループのフェロモンを撒き、グループ固有の濃度勾配が Cohesion に寄与します。
- `danger`: 敵接近や危険サインで蓄積され、勾配や局所濃度が高いセルではエージェントが Flee 行動を選好します。

---

## Unity での表示

1. Unity Hub で本リポジトリを開き、Unity 6.x LTS でロード。
2. シーンとして `Assets/Scenes/Terrarium.unity` を開いて `Play` を押すと、固定カメラ視点でキューブ群の挙動を確認できます。
3. 表示側では `src/Unity/` のマッピングコードを通じて Simulation から受け取ったスナップショットを GPU インスタンシングで描画します。Sim 側のロジックは描画事情で止めないでください。
4. `TerrariumHost` (`src/Unity/TerrariumHost.cs`) をシーンに置き、インスペクタでタイムステップや初期個体数などを設定。`CubeInstancedRenderer` を同じオブジェクトまたは別オブジェクトにアタッチし、インスペクタの `Renderer` フィールドにアサインするか、別スクリプトから `RenderWith(...)` を呼び出します。
5. `CubeInstancedRenderer` (`src/Unity/CubeInstancedRenderer.cs`) はキューブメッシュと GPU インスタンシング対応マテリアルをシリアライズフィールドで受け取り、毎フレーム `Render` でスナップショット配列を描画します。色は `AgentSnapshot.ColorHue` を HSV→RGB 変換してインスタンス毎に適用します。

---

## ドキュメントと運用

- 設計思想・アルゴリズムの詳細: [`docs/DESIGN.md`](docs/DESIGN.md)
- ExecPlan の書き方・運用ルール: [`.agent/PLANS.md`](.agent/PLANS.md)
- 長時間観察時のメトリクスやフィードバックの検証手順は `AGENTS.md` も参照してください。

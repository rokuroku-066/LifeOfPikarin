# Life Of Pikarin

俯瞰固定カメラでキューブたちが自律的に動き回る箱庭（Alife）シミュレーションです。Phase 1 では **キューブ表示のみ**を対象とし、後から FBX モデル・アニメーションに差し替え可能な構造になっています。

- シミュレーションは **長時間連続稼働** を想定
- 個体は成長・繁殖・死などのライフサイクルを持つ
- SpatialGrid を用いた近傍検索で **O(N²) を回避**
- 複数のグループ（コロニー）が自然に形成されるようなルール設計
- モデル表示は Phase 1 では **キューブ＋GPUインスタンシング**
- コードベースは Codex 用の `AGENTS.md` / `PLANS.md` と連携

詳細なシステム設計は [`docs/DESIGN.md`](docs/DESIGN.md) を参照してください。

---

## 🧩 プロジェクトの現状

- **Simulation**: `src/Sim/` にエンジン非依存の C# コアを実装。
- **Visualization**: Unity 側の表示レイヤーは `src/Unity/` のマッピングコードをベースに、キューブの GPU インスタンシング表示を行う想定。
- **Headless 実行**: `src/SimRunner/` のコンソールアプリでシミュレーションをステップ実行し、CSV でメトリクスを出力可能。
- **テスト**: `tests/SimTests/` にシミュレーションの決定性・フィードバック・グリッド近傍検索などのユニットテストを収録。

---

## 🧰 必要環境

| 目的 | 必須ツール | 備考 |
| --- | --- | --- |
| Unity での表示 | **Unity 6.3 LTS**（6.x LTS 系列推奨） | Unity Hub からインストールし、このリポジトリを開く |
| シミュレーション実行・テスト | **.NET 8 SDK** | `dotnet --info` で 8 系が見えることを確認 |
| バージョン管理 | Git | 任意のクライアントで OK |

> `.NET 8 SDK` のインストール手順は `AGENTS.md` にも記載があります。環境に合わせてセットアップしてください。

---

## 📁 ディレクトリ構成

```text
.
├── AGENTS.md             # Codex 向けガイド
├── .agent/PLANS.md       # ExecPlan の運用ルール
├── docs/DESIGN.md        # システム設計（Simulation / View / Grid 等）
├── src/
│   ├── Sim/              # シミュレーションコア（エンジン非依存 C#）
│   ├── SimRunner/        # ヘッドレス実行用コンソールアプリ
│   └── Unity/            # Unity 統合層（表示マッピングなど）
├── tests/SimTests/       # シミュレーションのユニットテスト
└── Terrarium.sln         # .NET ソリューション
```

---

## 🚀 セットアップ手順

1. リポジトリをクローン
   ```bash
git clone <このリポジトリのURL>
cd LifeOfPikarin
```
2. .NET SDK をインストールして `dotnet --info` で 8.x が利用できることを確認。
3. Unity 6.x LTS（推奨: 6.3 LTS）を Unity Hub からインストールし、プロジェクトを開く。
   - Windows では `setup_windows_env.bat` をルートで実行すると、.NET 8 SDK の導入確認と Unity Hub / Unity 6.x LTS の有無チェック、ソリューション復元、テスト実行までまとめて行えます。

---

## ▶️ シミュレーションの実行（ヘッドレス）

`src/SimRunner/` のコンソールアプリで指定ステップ分のシミュレーションを回し、CSV にメトリクスを書き出します。

```bash
dotnet run --project src/SimRunner \
  -- --steps 2000 --seed 1337 \
  --initial 120 --max 500 \
  --log artifacts/metrics.csv
```

出力される CSV のカラム例:

- `tick`: シミュレーションステップ
- `population`: 生存個体数
- `births` / `deaths`: ステップ中の出生・死亡数
- `avgEnergy` / `avgAge`: 平均エネルギー・平均年齢
- `groups`: グループ（群れ）数
- `neighborChecks`: 近傍判定のカウント（O(N²) を避けるための指標）
- `tickDurationMs`: 1 ステップの処理時間（ms）

`--log` で指定したパス配下にディレクトリが無ければ自動で作成されます。

---

## 🧪 テスト

シミュレーションコアの決定性や環境システムの安定性はユニットテストで確認できます。

```bash
dotnet test tests/SimTests/SimTests.csproj
```

- 固定シードでの結果一致、近傍検索の範囲制限、負のフィードバックによる個体数抑制、メトリクス CSV 出力などをカバーしています。

---

## 🎨 Unity での表示

1. Unity Hub でこのリポジトリを開き、Unity 6.x LTS でロードします。
2. シーン（例: `Assets/Scenes/Terrarium.unity`）を開いて `Play` を押すと、固定カメラ視点でキューブ群の挙動が確認できます。
3. 表示側では `src/Unity/` のマッピングコードを通じて、Simulation から受け取ったスナップショットを GPU インスタンシングで描画する想定です。Sim 側のロジックは描画事情で止めないようにしてください。
4. `TerrariumHost` (`src/Unity/TerrariumHost.cs`) をシーンに置き、インスペクタでタイムステップや初期個体数などを設定します。`CubeInstancedRenderer` を同じオブジェクトまたは別オブジェクトにアタッチし、ホストの `Renderer` フィールドにアサインするか、別スクリプトから `RenderWith(...)` を呼び出してください。
5. `CubeInstancedRenderer` (`src/Unity/CubeInstancedRenderer.cs`) はキューブメッシュ＋GPU インスタンシング対応マテリアルをシリアライズフィールドで受け取り、毎フレーム `Render` でスナップショット配列を描画します。色は `AgentSnapshot.ColorHue` を HSV→RGB 変換してインスタンス毎に適用します。

---

## 📓 ドキュメントと運用

- 設計思想・アルゴリズムの詳細: [`docs/DESIGN.md`](docs/DESIGN.md)
- ExecPlan の書き方・運用ルール: [`.agent/PLANS.md`](.agent/PLANS.md)
- 長時間観察時のメトリクスや負のフィードバックの検証手順は `AGENTS.md` のバリデーション節も参照してください。

# Life Of Pikarin

俯瞰固定カメラでキューブたちが�E律的に動き回る箱庭�E�Elife�E�シミュレーションです。Phase 1 では **キューブ表示のみ**を対象とし、後かめEFBX モチE��・アニメーションに差し替え可能な構造になってぁE��す、E

- シミュレーションは **長時間連続稼僁E* を想宁E
- 個体�E成長・繁殖�E死などのライフサイクルを持つ
- SpatialGrid を用ぁE��近傍検索で **O(N²) を回避**
- 褁E��のグループ（コロニ�E�E�が自然に形成されるようなルール設訁E
- モチE��表示は Phase 1 では **キューブ＋GPUインスタンシング**
- コード�Eースは Codex 用の `AGENTS.md` / `PLANS.md` と連携

詳細なシスチE��設計�E [`docs/DESIGN.md`](docs/DESIGN.md) を参照してください、E

---

## 🧩 プロジェクト�E現状

- **Simulation**: `src/Sim/` にエンジン非依存�E C# コアを実裁E��E
- **Visualization**: Unity 側の表示レイヤーは `src/Unity/` のマッピングコードをベ�Eスに、キューブ�E GPU インスタンシング表示を行う想定、E
- **Headless 実衁E*: `src/SimRunner/` のコンソールアプリでシミュレーションをスチE��プ実行し、CSV でメトリクスを�E力可能、E
- **チE��チE*: `tests/SimTests/` にシミュレーションの決定性・フィードバチE��・グリチE��近傍検索などのユニットテストを収録、E

---

## 🧰 忁E��環墁E

| 目皁E| 忁E��ツール | 備老E|
| --- | --- | --- |
| Unity での表示 | **Unity 6.3 LTS**�E�E.x LTS 系列推奨�E�E| Unity Hub からインスト�Eルし、このリポジトリを開ぁE|
| シミュレーション実行�EチE��チE| **.NET 8 SDK** | `dotnet --info` で 8 系が見えることを確誁E|
| バ�Eジョン管琁E| Git | 任意�Eクライアントで OK |

> `.NET 8 SDK` のインスト�Eル手頁E�E `AGENTS.md` にも記載があります。環墁E��合わせてセチE��アチE�Eしてください、E

---

## 📁 チE��レクトリ構�E

```text
.
├── AGENTS.md             # Codex 向けガイチE
├── .agent/PLANS.md       # ExecPlan の運用ルール
├── docs/DESIGN.md        # シスチE��設計！Eimulation / View / Grid 等！E
├── src/
━E  ├── Sim/              # シミュレーションコア�E�エンジン非依孁EC#�E�E
━E  ├── SimRunner/        # ヘッドレス実行用コンソールアプリ
━E  └── Unity/            # Unity 統合層�E�表示マッピングなど�E�E
├── tests/SimTests/       # シミュレーションのユニットテスチE
└── Terrarium.sln         # .NET ソリューション
```

---

## 🚀 セチE��アチE�E手頁E

1. リポジトリをクローン
```bash
git clone https://github.com/rokuroku-066/LifeOfPikarin.git
cd LifeOfPikarin
```
2. .NET SDK をインスト�Eルして `dotnet --info` で 8.x が利用できることを確認、E
3. Unity 6.x LTS�E�推奨: 6.3 LTS�E�を Unity Hub からインスト�Eルし、�Eロジェクトを開く、E
   - Windows では `setup_windows_env.bat` をルートで実行すると、ENET 8 SDK の導�E確認と Unity Hub / Unity 6.x LTS の有無チェチE��、ソリューション復允E��テスト実行までまとめて行えます、E

---

## ▶�E�Eシミュレーションの実行（�EチE��レス�E�E

`src/SimRunner/` のコンソールアプリで持E��スチE��プ�Eのシミュレーションを回し、CSV にメトリクスを書き�Eします、E

```bash
dotnet run --project src/SimRunner/SimRunner.csproj \
  -- --steps 3000 --seed 42 \
  --initial 120 --max 500 \
  --log artifacts/metrics_smoke.csv
```

出力される CSV のカラム侁E

- `tick`: �V�~�����[�V�����X�e�b�v
- `population`: �����̐�
- `births` / `deaths`: �X�e�b�v���̏o���E���S��
- `avgEnergy` / `avgAge`: ���σG�l���M�[�E���ϔN��
- `groups`: �O���[�v�i�Q��j���i������ 0�B�������̌̂̓J�E���g���Ȃ��j
- `neighborChecks`: �ߖT����̃J�E���g�iO(N2) ������邽�߂̃w���X�w�W�j
- `tickDurationMs`: 1 �X�e�b�v�̏������ԁi�~���b)

`--log` で持E��したパス配下にチE��レクトリが無ければ自動で作�Eされます、E
主要な調整パラメータ�E�ESimulationConfig` と Unity インスペクタの DTO が同じ頁E��を持ちます！E
- エネルギー上限と代謁E `EnergySoftCap`, `HighEnergyMetabolismSlope`, `MetabolismPerSecond`, `InitialEnergyFractionOfThreshold`
- 繁殖トリガ: `ReproductionEnergyThreshold`, `AdultAge`, `DensityReproductionSlope`, `DensityReproductionPenalty`
- 寿命/危険: `BaseDeathProbabilityPerSecond`, `AgeDeathProbabilityPerSecond`, `DensityDeathProbabilityPerNeighborPerSecond`
- 環墁E��ィールチE `FoodRegenPerSecond`, `FoodFromDeath`, `DangerDiffusionRate`/`DangerDecayRate`, `PheromoneDepositOnBirth`
- �Q��`��: `GroupFormationWarmupSeconds`, `GroupFormationChance`, `GroupAdoptionChance`, `GroupSplitChance` �Ȃǁi�����O���[�v���� 0�j

---

## 🧪 チE��チE

シミュレーションコアの決定性めE��墁E��スチE��の安定性はユニットテストで確認できます、E

```bash
dotnet test tests/SimTests/SimTests.csproj
```

- 固定シードでの結果一致、近傍検索の篁E��制限、負のフィードバチE��による個体数抑制、メトリクス CSV 出力などをカバ�EしてぁE��す、E

### 環墁E��ィールチE

`EnvironmentGrid` はセル毎に `food`・`pheromone`�E�グループ別�E��E`danger` の 3 スカラーフィールドを持ち、いずれも毎ティチE��で減衰�E�隣接セルへの拡散を行います、E

- `food`: パッチ定義で初期化され、時間経過で再生・拡散し、消費めE��亡で追加されます。`World.Step` の Forage 行動は `food` 勾配を優先します、E
- `pheromone`: 繁殖�E功地点で自グループ�Eフェロモンを撒き、グループ固有�E濁E��勾配が Cohesion に寁E��します、E
- `danger`: 敵接近や危険サインで蓁E��され、勾配や局所濁E��が高いセルではエージェントが Flee 行動を選好します、E

---

## 🎨 Unity での表示

1. Unity Hub でこ�Eリポジトリを開き、Unity 6.x LTS でロードします、E
2. シーン�E�侁E `Assets/Scenes/Terrarium.unity`�E�を開いて `Play` を押すと、固定カメラ視点でキューブ群の挙動が確認できます、E
3. 表示側では `src/Unity/` のマッピングコードを通じて、Simulation から受け取ったスナップショチE��めEGPU インスタンシングで描画する想定です。Sim 側のロジチE��は描画事情で止めなぁE��ぁE��してください、E
4. `TerrariumHost` (`src/Unity/TerrariumHost.cs`) をシーンに置き、インスペクタでタイムスチE��プや初期個体数などを設定します。`CubeInstancedRenderer` を同じオブジェクトまた�E別オブジェクトにアタチE��し、�Eスト�E `Renderer` フィールドにアサインするか、別スクリプトから `RenderWith(...)` を呼び出してください、E
5. `CubeInstancedRenderer` (`src/Unity/CubeInstancedRenderer.cs`) はキューブメチE��ュ�E�GPU インスタンシング対応�EチE��アルをシリアライズフィールドで受け取り、毎フレーム `Render` でスナップショチE��配�Eを描画します。色は `AgentSnapshot.ColorHue` めEHSV→RGB 変換してインスタンス毎に適用します、E

---

## 📓 ドキュメントと運用

- 設計思想・アルゴリズムの詳細: [`docs/DESIGN.md`](docs/DESIGN.md)
- ExecPlan の書き方・運用ルール: [`.agent/PLANS.md`](.agent/PLANS.md)
- 長時間観察時のメトリクスめE��のフィードバチE��の検証手頁E�E `AGENTS.md` のバリチE�Eション節も参照してください、E

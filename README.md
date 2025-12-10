# Life Of Pikarin

俯瞰固定カメラで、キューブたちが自律的に動き回る箱庭（Alife）シミュレーションです。  
Phase 1 では **キューブ表示のみ**を対象とし、後から FBX モデル・アニメーションに差し替え可能な構造になっています。

- シミュレーションは **長時間連続稼働** を想定
- 個体は成長・繁殖・死などのライフサイクルを持つ
- 複数のグループ（コロニー）が自然に形成されるようなルール設計
- モデル表示は Phase 1 では **キューブ＋GPUインスタンシング**
- コードベースは Codex 用の `AGENTS.md` / `PLANS.md` と連携

詳細なシステム設計は [`docs/DESIGN.md`](docs/DESIGN.md) を参照してください。

---

## 🧩 技術スタック・前提

### Unity

- 推奨エディタ: **Unity 6.3 LTS**  
  - Unity 6 系列の最新 LTS は 6.3 LTS で、長期サポートが提供されます。:contentReference[oaicite:0]{index=0}  
  - 新規プロジェクトを作る場合は **Unity Hub** から 6.3 LTS を選択してください。:contentReference[oaicite:1]{index=1}  

> すでに別バージョンの Unity でプロジェクトを作成している場合は、  
> この README のバージョン番号を自分の環境に合わせて読み替えてください。

### 開発環境

- OS:  
  - Windows 10 以降 / macOS 12 以降 / Linux（Unity 対応ディストリ）
- 必須ツール:
  - [Unity Hub](https://unity.com/download)  
  - Unity 6.x LTS（推奨: 6.3 LTS）
- 推奨:
  - Git（バージョン管理）
  - VS Code / Rider / Visual Studio など C# 対応エディタ

### Codex（任意）

- このリポジトリは **OpenAI Codex** での開発を前提に `AGENTS.md` / `PLANS.md` を用意しています。
- Codex は `AGENTS.md` を自動で読み込み、開発ルールやビルド・テスト手順を把握します。:contentReference[oaicite:2]{index=2}  
- 複雑なタスクや長時間タスクでは `PLANS.md` に ExecPlan（実行計画）を作成し、それに沿って作業する運用を想定しています。:contentReference[oaicite:3]{index=3}  

---

## 📁 ディレクトリ構成（想定）

実際の構成はプロジェクトの進行にあわせて変わる可能性がありますが、Phase 1 の想定は以下です。

```text
.
├── AGENTS.md             # Codex 向けガイド
├── .agent/
│   └── PLANS.md          # ExecPlan の運用ルール
├── docs/
│   └── DESIGN.md         # システム設計（Simulation / View / Grid 等）
├── src/
│   ├── Sim/              # シミュレーションコア（エンジン非依存 C#）
│   └── Unity/            # Unity 統合層（MonoBehaviour / Renderer など）
└── Assets/
    ├── Scenes/
    │   └── Terrarium.unity   # メインの箱庭シーン（想定）
    └── Scripts/              # Unity 用のスクリプト（ラッパー層）
````

> `docs/DESIGN.md` に Simulation / Visualization の役割分担・アルゴリズム・グリッド設計などが書かれている前提です。

---

## 🚀 環境構築手順

### 1. リポジトリをクローン

```bash
git clone <このリポジトリのURL>
cd <クローンしたディレクトリ>
```

### 2. Unity Hub でプロジェクトを開く

1. Unity Hub を起動
2. 「Open」→ このリポジトリのディレクトリを選択
3. Unity 6.x LTS（推奨: 6.3 LTS）で開く

> 初回はライブラリの再インポートで時間がかかることがあります。

### 3. シーンを開く

Unity エディタ上で:

1. `Assets/Scenes/Terrarium.unity` をダブルクリック
2. 階層（Hierarchy）に `TerrariumRoot` などの管理オブジェクトが表示されていればOK

※ シーン名やオブジェクト名はプロジェクトで調整して構いません。
　README 内の名前と異なる場合は、自分の構成に置き換えてください。

---

## ▶️ 実行方法（エディタ内）

1. Unity エディタの上部メニューから `Play` ボタン（三角アイコン）をクリック
2. シミュレーションが開始されると、シーン内に

   * キューブの群れがランダムに初期配置される
   * 時間とともに移動・群れ形成・分散が起きる
3. 固定カメラ（俯瞰ビュー）が箱庭全体を見下ろす形になっている前提です

### カメラ制御（想定）

* Phase 1 では「固定カメラ」を推奨

  * 例えば `MainCamera` が箱庭中心を見下ろす位置（真上 or 斜め上）に配置されている構成。
* 必要に応じて

  * `CameraController` スクリプトで

    * 軽いパン/ズーム
    * スクリーンスペースへのフィット
      を実装しても構いません（ただし Sim ロジックには影響しないようにしてください）。

---

## 🧪 テスト方法

Phase 1 では主に **2種類のテスト** を想定しています。

1. **シミュレーションコアのテスト（C# / エンジン非依存）**
2. **Unity エディタ上での動作確認（視覚テスト）**

### 1. シミュレーションコアのテスト

`src/Sim/` 以下のロジックは、可能な限り Unity 非依存の C# コードとして実装します。

#### 1-1. 単体テスト（Unit Test）

* 推奨: `NUnit` または Unity Test Framework（PlayMode / EditMode Tests）
* 例: 以下のような観点をテストしてください。

  * 固定シード + 固定ステップ数での結果が再現されるか
  * SpatialGrid の近傍検索が O(N²) になっていないか（近傍数が上限内か）
  * 負のフィードバックが有効に働き、
    一定時間後の個体数が想定レンジに収まるか（爆発しない / 即死しない）

#### 1-2. ヘッドレス・ステップテスト（コンソール）

* エディタを使わずシミュレーションだけを回す「ステップ実行ツール」を用意することを推奨します。

  * 例: `src/Sim/Runner` 的な小さなコンソールアプリ／エディタスクリプト
* コマンド例（コンソールアプリを想定）:

```bash
dotnet run --project src/SimRunner \
  --steps 10000 \
  --seed 12345 \
  --log stats.csv
```

* 出力される `stats.csv` には

  * step
  * population
  * births
  * deaths
  * avgEnergy
  * avgAge
  * groupCount
    などのカラムを持たせると分析しやすくなります。

> `.NET` を使わない構成の場合は、Unity エディタの EditMode Tests や
> Editor 拡張から同等の「ステップ実行＆ログ出力」を実装してください。

### 2. Unity 上での視覚テスト

1. シーンを開いた状態で `Play` を押す
2. 少なくとも数分〜数十分程度走らせる
3. 以下の点をチェック：

   * キューブは自然なスピードで移動しているか（急激なワープや震えがない）
   * 群れが1つに完全に収束して団子状態になり続けていないか
   * 一定時間後に個体数が意味のある範囲で推移しているか
   * 画面全体を見ても、複数のグループがなんとなく分かれて存在しているように見えるか

長時間観察用の作品として使う場合は、
**1時間以上の連続実行** で安定するかも合わせて確認することをおすすめします。

---

## 📦 ビルド & デプロイ

Phase 1 の想定では、主に「ローカル実行用ビルド」をターゲットにします。
（展示や上映向けの本番ビルドについては、後に別途 `docs/DEPLOY.md` を用意しても良いです）

### 対象プラットフォーム

* Windows Standalone（x86_64）
* macOS Standalone
* Linux Standalone

### ビルド手順（Unity エディタ）

1. `File > Build Settings...` を開く
2. `Scenes In Build` に `Assets/Scenes/Terrarium.unity` が含まれていることを確認
3. ターゲットプラットフォームを選択（例: Windows）
4. `Build` または `Build And Run` をクリック
5. 出力された実行ファイルを起動すると、箱庭シミュレーションが全画面またはウィンドウで開始されます

### 展示・上映向け設定のヒント

* 自動で `Play` 状態に入るブートストラップシーンを作成しておくと、起動後の操作が不要になります。
* `Application.targetFrameRate` を明示し、マシンスペックに対して安定したフレームレートを保つように調整してください。
* GPU 負荷が高い場合は

  * 同時表示する個体数
  * インスタンシングのバッチサイズ
  * ポストエフェクト
    を調整して負荷を下げてください。

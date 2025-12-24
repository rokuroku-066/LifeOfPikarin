# Phase 2 設計書

**対象:** 「長期稼働キューブ・テラリウム」Phase 1 のSimを維持し、Viewerを **ぴかりん静的モデル + 背景（床+壁2面） + 斜め固定カメラ**へ刷新する。

---

## 0. スコープ 🎯

### 0.1 目的

* Viewer表示を **キューブ → ぴかりん（静的3Dモデル）**へ置換
* 背景を **床テクスチャ + 壁2面テクスチャ**にする（箱庭のコーナー）
* カメラは **斜め固定 1台のみ**（UI操作なし）
* WebSocketスナップショットを **補間描画**（Simと分離、Simに影響させない）

### 0.2 非目的（Phase 3+）

* アニメーション（リグ/モーション/ブレンド）
* 地形、空、ポストエフェクト、影（必要なら後で）

---

## 1. 基本原則 🧠

* **Sim/View完全分離**：Simは `World.step` のみで進行。Viewerは受け取ったスナップショットを補間して描画するだけ。
* **決定性はSim側で担保**：Viewerは非決定的でもOK（ただしID再利用などで破綻しない実装）。
* **大量表示前提**：最大 `max_population=700` を破綻なく表示できること。

---

## 2. 技術構成（Viewer）🔧

### 2.1 推奨方式

* **Three.js + WebGL**
* ぴかりん描画：**InstancedMesh**（GPUインスタンシング）
* モデル形式：**glTF 2.0 / GLB**

### 2.2 代替方式（将来検討枠）

* Babylon.js / Unity WebGL / Godot Web など
  （ただしPhase 2は変更最小のため Three.js 継続を採用）

---

## 3. アセット仕様 🎨

### 3.1 ぴかりん（静的モデル）

* ファイル：`static/assets/pikarin.glb`
* 推奨構成（重要）：

  * `Pikarin_Body`（ボディ）…色替え対象
  * `Pikarin_Face`（顔デカール）…固定表示（色替えしない）
* 座標/向き/ピボット規約：

  * **前向き：+Z**
  * **接地：足元がY=0**
  * スケール基準：`MODEL_BASE_SCALE` で調整（Phase1の cube=0.8 相当の見え方へ）
* マテリアル規約：

  * Body：`MeshStandardMaterial`（`vertexColors=true`）
  * Face：テクスチャ + 透過（`transparent=true`, `alphaTest=0.5` 推奨）

### 3.2 背景テクスチャ

* 床：`static/assets/ground.png`
* 壁（2面）：

  * `static/assets/wall_back.png`（奥壁）
  * `static/assets/wall_side.png`（左壁）

---

## 4. 座標系・変換ルール 📐

* Sim座標：`x,y ∈ [0, worldSize]`（worldSize=100）
* Viewer座標（Three.js）：

  * `x_view = agent.x - halfWorld`
  * `z_view = agent.y - halfWorld`
  * `y_view = 0`（地面上）
* 回転（yaw）：

  * `yaw = heading` をY軸回転に適用
  * 必要なら `MODEL_YAW_OFFSET` を加算（モデル正面補正）

---

## 5. 背景（床 + 壁2面）仕様 🧱

### 5.1 パラメータ

* `worldSize = 100`
* `halfWorld = 50`
* `WALL_HEIGHT = worldSize * 0.45`（推奨）

### 5.2 ジオメトリ配置

* 床（Floor）

  * `PlaneGeometry(worldSize, worldSize)`
  * `rotateX(-π/2)`、`position.y = 0`
* 奥壁（Back wall）

  * `PlaneGeometry(worldSize, WALL_HEIGHT)`
  * `position = (0, WALL_HEIGHT/2, -halfWorld - ε)`（ε=0.001程度）
  * 法線が内側（+Z）を向くよう回転
* 左壁（Side wall）

  * `PlaneGeometry(worldSize, WALL_HEIGHT)`
  * `position = (-halfWorld - ε, WALL_HEIGHT/2, 0)`
  * 法線が内側（+X）を向くよう回転

### 5.3 テクスチャ設定

* 色空間：`SRGBColorSpace`（床/壁/顔すべて）
* 床：`RepeatWrapping` + タイル（例：repeat=6〜10）
* 壁：基本 `ClampToEdgeWrapping`（repeat=1）

---

## 6. カメラ（固定斜め・1台）📷

* `PerspectiveCamera` 1台のみ（操作UIなし）
* 推奨初期値：

  * `fov = 60`
  * `pos = ( +halfWorld*0.55, worldSize*0.22, +halfWorld*0.65 )`
  * `lookAt(0, 0, 0)`
* リサイズ対応：

  * `camera.aspect = width/height`
  * `camera.updateProjectionMatrix()`

---

## 7. ライティング 🌟

* `AmbientLight`（弱め：0.3〜0.4）
* `DirectionalLight`（強め：0.8〜1.0）
* 影はPhase 2では **無効**（軽量優先）

---

## 8. ぴかりん群れ描画（Instancing）💠

### 8.1 生成

* GLB読み込み後、最大数 `MAX_INSTANCES = 700` でInstancedMeshを確保
* Meshが2つ（Body/Face）の場合：

  * `instancedBody`（instanceColor更新）
  * `instancedFace`（色固定、同じ行列だけ更新）

### 8.2 更新（毎フレーム）

* WebSocketで受信した `prevSnapshot / nextSnapshot` を使い補間係数 `alpha` を算出
* 各エージェント i について：

  * 位置：`(x_view, 0, z_view)`
  * 回転：`(0, yaw + MODEL_YAW_OFFSET, 0)`
  * スケール：`computeScale(...) * MODEL_BASE_SCALE`
  * 色（Bodyのみ）：`computeColor(...)` → `instanceColor`
* `mesh.count = population` で表示数を制御

---

## 9. スナップショット要件（Sim側変更なし）📡

Viewerが必要とする最低フィールド（現状のままでOK）：

* `agents[].id, x, y, vx, vy, heading, size, energy, age, group, lineage_id, trait_speed, behavior_state`
* `metrics.population, metrics.average_energy`（任意：見た目調整に利用）

将来拡張予約（Phase 2では未使用）：

* `appearance_seed`（個体差）
* `anim_state, anim_t`（Phase 3以降）

---

## 10. 実装変更点（app.jsの整理方針）🧹

### 削除

* 3分割ビュー（scissor/viewport）
* top/povカメラ、追跡ロジック
* OrbitControls

### 残す

* WS接続、スナップショット補間
* `computeColor / computeScale` 系
* pixelRatio自動調整（負荷安定）

### 追加

* GLBローダ（`GLTFLoader`）による pikarin 読み込み
* 背景（床+壁2面）のテクスチャ貼りPlane生成
* Body/Faceの二重Instancing（推奨）

---

## 11. 受け入れ条件（Done）✅

* 斜め固定カメラで **床+壁2面**が常に視界に入り、箱庭コーナーが成立
* ぴかりんが **200体以上**表示され、補間で滑らかに移動
* ボディ色は群れ/エネルギーで変化し、**顔は変色しない**
* `max_population=700` でもクラッシュせず動く（fpsは端末相応でOK）

---

## 12. 検証手順 🧪

1. `uvicorn terrarium.app.server:app --reload --port 8000`
2. ブラウザで確認：

   * GLBロード成功（失敗時はキューブフォールバック or ロード表示）
   * 背景：床+壁2面に画像が貼られている
   * カメラ固定（操作で動かない）
   * Start/Stop/Reset/Speed が従来通り機能

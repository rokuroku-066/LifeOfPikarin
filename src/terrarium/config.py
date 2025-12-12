from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class SpeciesConfig:
    base_speed: float = 6.0  # 基本移動速度。上げると活発だが衝突・消費が増えやすい。
    max_acceleration: float = 20.0  # 最大加速度。ターン性能の上限。高すぎると挙動が不安定に見える。
    vision_radius: float = 8  # 知覚半径。広げると群れ形成が進むが計算量と密集度が上がる。
    metabolism_per_second: float = 0.8  # 代謝（毎秒エネルギー消費）。大きくすると飢餓が早まり個体数抑制に効く。
    birth_energy_cost: float = 8.0  # 出産コスト。高いほど出生が減り、低すぎると爆発的に増える。
    reproduction_energy_threshold: float = 12.0  # 繁殖に必要な最小エネルギー。出生頻度を直接制御。
    adult_age: float = 20.0  # 成体とみなす年齢。成長演出や行動切替の基準に利用。
    initial_age_min: float = 0.0  # 初期年齢の最小値。0 で全員幼体スタート。
    initial_age_max: float = 0.0  # 初期年齢の最大値。幅を持たせると寿命分散で安定性が増す。
    max_age: float = 80.0  # 平均寿命の上限。減らすと世代交代が早まり、増やすと長期密度が上がる。
    wander_jitter: float = 0.45  # ランダム遊泳の揺らぎ強度。大きいと軌跡が散り、群れがほどけやすい。
    initial_energy_fraction_of_threshold: float = 0.8  # 初期エネルギーを閾値比で指定。低いと初期死が増える。
    energy_soft_cap: float = 20.0  # エネルギーのソフト上限。これを超えると余剰を使いづらくする。
    high_energy_metabolism_slope: float = 0.015  # 高エネルギー帯の追加代謝率。富んだ個体を自然に減速させる。


@dataclass
class ResourcePatchConfig:
    position: tuple[float, float] = (0.0, 0.0)  # パッチ中心座標。マップ上の給餌スポット位置。
    radius: float = 5.0  # パッチ半径。広げると到達しやすくなり群れが集まりやすい。
    resource_per_cell: float = 16.0  # セルあたり資源量の上限。食糧密度の天井。
    regen_per_second: float = 0.5  # 再生速度。高いほど持続供給、低いと枯渇しやすい。
    initial_resource: float = 10.0  # 初期資源量。スタート直後の飢餓抑制に効く。


@dataclass
class EnvironmentConfig:
    food_per_cell: float = 10.0  # ベース食糧量（グリッドセル上限）。上げると全体に飢餓が減る。
    food_regen_per_second: float = 0.5  # 再生速度。高いと持続的な餌場、低いと枯渇による間引きが起きやすい。
    food_consumption_rate: float = 5.0  # 摂食レート。上げると短時間で満腹になるが資源枯渇も早い。
    food_diffusion_rate: float = 0.0  # 食糧の拡散率。>0 で平滑化し、局所濃度差が減る。
    food_decay_rate: float = 0.0  # 食糧の自然減衰。腐敗を表現。増やすと空腹圧が強まり密度抑制。
    food_from_death: float = 3.0  # 死亡時に残す食糧量。高いと死体を起点に群れが形成されやすい。
    resource_patches: List[ResourcePatchConfig] = field(default_factory=list)  # 追加の資源パッチ設定リスト。
    danger_diffusion_rate: float = 2.0  # 危険シグナルの拡散。高いと逃避が連鎖しやすい。
    danger_decay_rate: float = 1.0  # 危険シグナルの減衰。低いと恐怖が長引き行動が鈍る。
    danger_pulse_on_flee: float = 1.0  # 逃走時に発する危険量。群衆パニックの強さを決める。
    pheromone_diffusion_rate: float = 0.1  # フェロモン拡散。トレイルをどれだけ広げるか。
    pheromone_decay_rate: float = 0.0  # フェロモン減衰。高いとすぐ消え、低いと持続的な道標になる。
    pheromone_deposit_on_birth: float = 4.0  # 誕生時のフェロモン量。出生地点の可視化・群れ誘引に。


@dataclass
class FeedbackConfig:
    local_density_soft_cap: int = 15  # この近傍数を超えると各種ペナルティが効き始める密度目安。
    density_reproduction_penalty: float = 0.6  # 高密度時の繁殖低減係数。1 に近いと抑制弱、0 で繁殖停止。
    stress_drain_per_neighbor: float = 0.01  # 近傍1体あたりのストレス増分。群れ密度抑制の主因。
    disease_probability_per_neighbor: float = 0.002  # 近傍1体あたりの感染確率/秒。密集のリスクを表す。
    density_reproduction_slope: float = 0.02  # 密度による繁殖ペナルティ勾配。急にしたいなら上げる。
    base_death_probability_per_second: float = 0.0005  # 基本死亡確率/秒。全体の寿命スケール調整。
    age_death_probability_per_second: float = 0.00015  # 年齢由来の死亡確率/秒。老化の強さ。
    density_death_probability_per_neighbor_per_second: float = 0.0001  # 密度由来死亡。高いと過密が即死に繋がる。

    group_formation_warmup_seconds: float = 0.0  # シミュ開始直後に群形成を抑える猶予時間。
    group_formation_neighbor_threshold: int = 5  # 群形成に必要な近傍数。低いほど小集団ができやすい。
    group_formation_chance: float = 0.02  # 条件成立時の形成確率/秒。群れ出現の頻度。
    group_adoption_neighbor_threshold: int = 2  # 既存群への参加に必要な近傍数。高いと参加が進みにくい。
    group_adoption_chance: float = 0.05  # 参加確率/秒。群れの吸着速度。
    group_split_neighbor_threshold: int = 10  # 分裂判定近傍数。高いと大きな群れだけが割れる。
    group_split_chance: float = 0.0015  # 分裂確率/秒。低いほど群れは粘る。
    group_split_new_group_chance: float = 0.7  # 分裂時に新規グループとして独立する確率。0 なら既存群残留。
    group_split_stress_threshold: float = 0.4  # このストレス以上で分裂判定を有効化。緊張が高いと割れやすい。
    group_birth_seed_chance: float = 0.35  # 誕生イベントが新規群シードになる確率。群れの芽をどれだけ撒くか。
    group_mutation_chance: float = 0.05  # 群属性の突然変異確率。高いと多様性が増すが挙動が不安定に。
    group_cohesion_radius: float = 6.0  # 群れ中心への結束距離。大きいとまとまりやすいが密集しがち。
    group_detach_radius: float = 3.0  # 離脱を考える距離。小さいほど群れを維持しやすい。
    group_detach_close_neighbor_threshold: int = 3  # 近傍がこの数以下なら離脱を許容。孤立度の基準。
    group_detach_after_seconds: float = 5.0  # 上記条件が続いた時間。長いほど粘り強く群に留まる。
    group_switch_chance: float = 0.2  # 近くの別群へ乗り換える確率/秒。高いと群れの流動性が増す。
    group_cohesion_weight: float = 0.8  # 群れへの追従強度（力重み）。上げると固まり、下げると拡散。


@dataclass
class SimulationConfig:
    time_step: float = 1.0 / 50.0  # シミュレーション固定刻み秒。小さくすると精度↑計算量↑。
    initial_population: int = 120  # 初期個体数。高すぎると初期フレームで密度ペナルティが発火。
    max_population: int = 700  # 個体数上限。安全弁。突発的増殖を防ぐ。
    world_size: float = 100.0  # 世界の一辺サイズ。広げると密度が下がり、行動が疎になる。
    cell_size: float = 2.5  # 空間ハッシュのセル幅。視野よりやや小さく設定すると近傍検索が効率的。
    seed: int = 1337  # 乱数シード。再現性確保のキー。変更で初期配置や挙動が変わる。
    config_version: str = "v1"  # 設定バージョン識別子。外部ファイル互換のために更新する。
    species: SpeciesConfig = field(default_factory=SpeciesConfig)  # 個体特性セット。
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)  # 環境と資源の設定。
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)  # フィードバック・群挙動の設定。

    @staticmethod
    def from_yaml(path: Path) -> "SimulationConfig":
        data = yaml.safe_load(Path(path).read_text())
        return load_config(data)


@dataclass
class AppConfig:
    simulation: SimulationConfig = field(default_factory=SimulationConfig)  # シミュレーション全体設定。
    broadcast_interval: int = 2  # 状態ブロードキャスト間隔（秒）。UI更新頻度の目安。


def load_config(raw: dict) -> SimulationConfig:
    species = SpeciesConfig(**raw.get("species", {}))
    patches = [ResourcePatchConfig(**patch) for patch in raw.get("resource_patches", raw.get("ResourcePatches", []))]
    env_raw = raw.get("environment", {})
    env = EnvironmentConfig(
        resource_patches=patches,
        **{k: v for k, v in env_raw.items() if k != "resource_patches"},
    )
    feedback = FeedbackConfig(**raw.get("feedback", {}))
    sim_values = {k: v for k, v in raw.items() if k not in {"species", "environment", "feedback", "resource_patches"}}
    return SimulationConfig(species=species, environment=env, feedback=feedback, **sim_values)

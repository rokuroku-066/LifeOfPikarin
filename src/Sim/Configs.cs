using System;
using System.Collections.Generic;

namespace Terrarium.Sim
{
    public sealed class SimulationConfig
    {
        public float TimeStep { get; set; } = 1f / 30f; // 固定シミュレーション刻み秒
        public int InitialPopulation { get; set; } = 120; // 初期生成する個体数
        public int MaxPopulation { get; set; } = 500; // 個体数の上限（出生を抑制）
        public float WorldSize { get; set; } = 100f; // ワールド一辺の長さ
        public float CellSize { get; set; } = 2.5f; // 空間ハッシュのセル幅
        public int Seed { get; set; } = 1337; // 乱数シード（決定性のため）
        public SpeciesConfig Species { get; set; } = new(); // 種固有パラメータ群
        public EnvironmentConfig Environment { get; set; } = new(); // 環境・資源パラメータ群
        public FeedbackConfig Feedback { get; set; } = new(); // 密度フィードバック等の制御パラメータ
    }

    public sealed class SpeciesConfig
    {
        public float BaseSpeed { get; set; } = 6f; // 基本移動速度
        public float MaxAcceleration { get; set; } = 20f; // 最大加速度
        public float VisionRadius { get; set; } = 6f; // 視野半径（近傍探索の範囲）
        public float MetabolismPerSecond { get; set; } = 0.8f; // 毎秒の代謝消費エネルギー
        public float BirthEnergyCost { get; set; } = 8f; // 出産に必要なエネルギー消費量
        public float ReproductionEnergyThreshold { get; set; } = 12f; // 繁殖可能になるエネルギー閾値
        public float AdultAge { get; set; } = 20f; // 成体とみなす年齢（秒）
        public float InitialAgeMin { get; set; } = 0f; // 初期個体の年齢下限
        public float InitialAgeMax { get; set; } = 0f; // 初期個体の年齢上限（0 以下なら AdultAge と MaxAge/2 の低い方）
        public float MaxAge { get; set; } = 80f; // 寿命（この年齢以降死亡確率が上昇）
        public float WanderJitter { get; set; } = 0.45f; // ランダム遊泳の方向ジッタ強度
        public float InitialEnergyFractionOfThreshold { get; set; } = 0.8f; // 初期エネルギー（閾値に対する割合）
        public float EnergySoftCap { get; set; } = 20f; // エネルギーの緩い上限（これ以上でペナルティ）
        public float HighEnergyMetabolismSlope { get; set; } = 0.015f; // 高エネルギー時の追加代謝増加勾配
    }

    public sealed class EnvironmentConfig
    {
        public float FoodPerCell { get; set; } = 10f; // 各セルの初期餌量
        public float FoodRegenPerSecond { get; set; } = 0.5f; // 餌の毎秒再生量
        public float FoodConsumptionRate { get; set; } = 5f; // 1回の摂食で消費できる餌量
        public float FoodDiffusionRate { get; set; } = 0f; // 餌の拡散率
        public float FoodDecayRate { get; set; } = 0f; // 餌の自然減衰率
        public float FoodFromDeath { get; set; } = 1f; // 死亡時に残す餌量
        public IReadOnlyList<ResourcePatchConfig> ResourcePatches { get; set; } = Array.Empty<ResourcePatchConfig>(); // 資源パッチのリスト
        public float DangerDiffusionRate { get; set; } = 1f; // 危険シグナルの拡散率
        public float DangerDecayRate { get; set; } = 1f; // 危険シグナルの減衰率
        public float DangerPulseOnFlee { get; set; } = 1f; // 逃走時に放出する危険シグナル量
        public float PheromoneDiffusionRate { get; set; } = 0f; // フェロモンの拡散率
        public float PheromoneDecayRate { get; set; } = 0f; // フェロモンの減衰率
        public float PheromoneDepositOnBirth { get; set; } = 4f; // 出生時に残すフェロモン量
    }

    public sealed class ResourcePatchConfig
    {
        public Vec2 Position { get; set; } = new Vec2(0, 0); // パッチ中心座標
        public float Radius { get; set; } = 5f; // パッチ半径
        public float ResourcePerCell { get; set; } = 10f; // セルあたり供給される資源量
        public float RegenPerSecond { get; set; } = 0.5f; // パッチの毎秒再生量
        public float InitialResource { get; set; } = 10f; // パッチ初期資源量
    }

    public sealed class FeedbackConfig
    {
        public int LocalDensitySoftCap { get; set; } = 8; // 近傍セル密度のソフト上限
        public float DensityReproductionPenalty { get; set; } = 0.6f; // 上限超過時の繁殖係数ペナルティ
        public float StressDrainPerNeighbor { get; set; } = 0.05f; // 隣接1体あたりのストレス消耗/秒
        public float DiseaseProbabilityPerNeighbor { get; set; } = 0.002f; // 隣接1体あたりの疾病発生確率/秒
        public float DensityReproductionSlope { get; set; } = 0.04f; // 密度による繁殖低下の傾き
        public float BaseDeathProbabilityPerSecond { get; set; } = 0.0005f; // 基本死亡確率/秒
        public float AgeDeathProbabilityPerSecond { get; set; } = 0.00015f; // 加齢による死亡確率/秒
        public float DensityDeathProbabilityPerNeighborPerSecond { get; set; } = 0.0001f; // 隣接1体あたりの追加死亡確率/秒
    }
}

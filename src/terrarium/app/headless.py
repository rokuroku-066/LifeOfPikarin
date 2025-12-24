from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Optional

from ..sim.core.config import SimulationConfig
from ..sim.core.world import World


_BASIC_HEADER = [
    "tick",
    "population",
    "births",
    "deaths",
    "avg_energy",
    "avg_age",
    "groups",
    "neighbor_checks",
    "tick_ms",
]

_DETAILED_HEADER = [
    "tick",
    "population",
    "births",
    "deaths",
    "avg_energy",
    "avg_age",
    "groups",
    "ungrouped",
    "neighbor_checks",
    "tick_ms",
    "ungrouped_ratio",
    "births_per_agent",
    "deaths_per_agent",
    "neighbor_checks_per_agent",
    "tick_ms_per_agent",
    "avg_speed",
    "avg_stress",
    "max_stress",
    "avg_group_size",
    "min_group_size",
    "max_group_size",
    "occupied_cells",
    "avg_agents_per_cell",
    "max_cell_occupancy",
    "population_density",
    "group_stride",
    "group_stride_threshold",
    "group_stride_active",
    "group_stride_active_agents",
    "group_stride_skipped_agents",
]


def _format_basic_row(metrics: object, tick_ms: float) -> list[object]:
    return [
        metrics.tick,
        metrics.population,
        metrics.births,
        metrics.deaths,
        f"{metrics.average_energy:.4f}",
        f"{metrics.average_age:.4f}",
        metrics.groups,
        metrics.neighbor_checks,
        f"{tick_ms:.3f}",
    ]


def _format_detailed_row(world: World, metrics: object, tick: int, tick_ms: float) -> list[object]:
    population = metrics.population
    ungrouped = metrics.ungrouped
    if population <= 0:
        ungrouped_ratio = 0.0
        births_per_agent = 0.0
        deaths_per_agent = 0.0
        neighbor_checks_per_agent = 0.0
        tick_ms_per_agent = 0.0
        avg_speed = 0.0
        avg_stress = 0.0
        max_stress = 0.0
        avg_group_size = 0.0
        min_group_size = 0
        max_group_size = 0
        occupied_cells = 0
        avg_agents_per_cell = 0.0
        max_cell_occupancy = 0
        population_density = 0.0
        group_stride = max(1, int(world._config.feedback.group_update_stride))
        group_stride_threshold = max(0, int(world._config.feedback.group_update_population_threshold))
        group_stride_active = 0
        group_stride_active_agents = 0
        group_stride_skipped_agents = 0
    else:
        ungrouped_ratio = ungrouped / population
        births_per_agent = metrics.births / population
        deaths_per_agent = metrics.deaths / population
        neighbor_checks_per_agent = metrics.neighbor_checks / population
        tick_ms_per_agent = tick_ms / population

        config = world._config
        cell_size = config.cell_size
        group_stride = max(1, int(config.feedback.group_update_stride))
        group_stride_threshold = max(0, int(config.feedback.group_update_population_threshold))
        group_stride_active = int(population >= group_stride_threshold and group_stride > 1)
        group_stride_active_agents = 0

        speed_sum = 0.0
        stress_sum = 0.0
        max_stress = 0.0
        group_sizes: dict[int, int] = {}
        cell_counts: dict[tuple[int, int], int] = {}

        for agent in world.agents:
            if not agent.alive:
                continue
            velocity = agent.velocity
            speed_sum += math.hypot(velocity.x, velocity.y)
            stress = agent.stress
            stress_sum += stress
            if stress > max_stress:
                max_stress = stress

            group_id = agent.group_id
            if group_id >= 0:
                group_sizes[group_id] = group_sizes.get(group_id, 0) + 1

            cell_key = (int(agent.position.x // cell_size), int(agent.position.y // cell_size))
            cell_counts[cell_key] = cell_counts.get(cell_key, 0) + 1

            if group_stride_active and (tick + agent.id) % group_stride == 0:
                group_stride_active_agents += 1

        if not group_stride_active:
            group_stride_active_agents = population
        group_stride_skipped_agents = max(0, population - group_stride_active_agents)

        avg_speed = speed_sum / population
        avg_stress = stress_sum / population

        if group_sizes:
            group_count = len(group_sizes)
            grouped_total = sum(group_sizes.values())
            avg_group_size = grouped_total / group_count
            min_group_size = min(group_sizes.values())
            max_group_size = max(group_sizes.values())
        else:
            avg_group_size = 0.0
            min_group_size = 0
            max_group_size = 0

        occupied_cells = len(cell_counts)
        if occupied_cells > 0:
            avg_agents_per_cell = population / occupied_cells
            max_cell_occupancy = max(cell_counts.values())
        else:
            avg_agents_per_cell = 0.0
            max_cell_occupancy = 0

        world_area = config.world_size * config.world_size
        population_density = population / world_area if world_area > 0 else 0.0

    return [
        metrics.tick,
        population,
        metrics.births,
        metrics.deaths,
        f"{metrics.average_energy:.4f}",
        f"{metrics.average_age:.4f}",
        metrics.groups,
        ungrouped,
        metrics.neighbor_checks,
        f"{tick_ms:.3f}",
        f"{ungrouped_ratio:.4f}",
        f"{births_per_agent:.4f}",
        f"{deaths_per_agent:.4f}",
        f"{neighbor_checks_per_agent:.4f}",
        f"{tick_ms_per_agent:.4f}",
        f"{avg_speed:.4f}",
        f"{avg_stress:.4f}",
        f"{max_stress:.4f}",
        f"{avg_group_size:.4f}",
        min_group_size,
        max_group_size,
        occupied_cells,
        f"{avg_agents_per_cell:.4f}",
        max_cell_occupancy,
        f"{population_density:.6f}",
        group_stride,
        group_stride_threshold,
        group_stride_active,
        group_stride_active_agents,
        group_stride_skipped_agents,
    ]


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = (len(sorted_values) - 1) * percentile
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return float(sorted_values[low])
    weight = pos - low
    return float(sorted_values[low] + (sorted_values[high] - sorted_values[low]) * weight)


def _summary_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "max": 0.0, "avg": 0.0, "p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
    sorted_values = sorted(values)
    total = sum(values)
    count = len(values)
    return {
        "min": float(sorted_values[0]),
        "max": float(sorted_values[-1]),
        "avg": float(total / count),
        "p50": _percentile(sorted_values, 0.50),
        "p90": _percentile(sorted_values, 0.90),
        "p95": _percentile(sorted_values, 0.95),
        "p99": _percentile(sorted_values, 0.99),
    }


def _correlation(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = 0.0
    denom_x = 0.0
    denom_y = 0.0
    for x, y in zip(xs, ys):
        dx = x - mean_x
        dy = y - mean_y
        num += dx * dy
        denom_x += dx * dx
        denom_y += dy * dy
    denom = math.sqrt(denom_x * denom_y)
    if denom == 0.0:
        return 0.0
    return float(num / denom)


def run_headless(
    steps: int,
    seed: Optional[int],
    log_path: Optional[Path],
    deterministic_log: bool = False,
    log_format: str = "detailed",
    summary_path: Optional[Path] = None,
    summary_window: int = 5000,
) -> None:
    config = SimulationConfig()
    if seed is not None:
        config.seed = seed
    world = World(config)

    log_mode = log_format.lower().strip()
    if log_mode not in {"basic", "detailed"}:
        raise ValueError(f"Unknown log format: {log_format}")

    writer = None
    csv_file = None
    if log_path:
        csv_file = Path(log_path).open("w", newline="")
        writer = csv.writer(csv_file)
        writer.writerow(_DETAILED_HEADER if log_mode == "detailed" else _BASIC_HEADER)

    tick_ms_series: list[float] = []
    population_series: list[int] = []
    neighbor_checks_series: list[int] = []
    neighbor_checks_per_agent_series: list[float] = []
    max_tick_ms = (-1.0, -1)
    max_population = (-1, -1)
    max_neighbor_checks = (-1, -1)

    for tick in range(steps):
        metrics = world.step(tick)
        tick_ms = 0.0 if deterministic_log else metrics.tick_duration_ms

        if summary_path:
            tick_ms_series.append(tick_ms)
            population_series.append(metrics.population)
            neighbor_checks_series.append(metrics.neighbor_checks)
            neighbor_checks_per_agent_series.append(
                0.0 if metrics.population <= 0 else metrics.neighbor_checks / metrics.population
            )
            if tick_ms > max_tick_ms[0]:
                max_tick_ms = (tick_ms, tick)
            if metrics.population > max_population[0]:
                max_population = (metrics.population, tick)
            if metrics.neighbor_checks > max_neighbor_checks[0]:
                max_neighbor_checks = (metrics.neighbor_checks, tick)

        if writer:
            if log_mode == "detailed":
                writer.writerow(_format_detailed_row(world, metrics, tick, tick_ms))
            else:
                writer.writerow(_format_basic_row(metrics, tick_ms))

    if csv_file:
        csv_file.close()

    if summary_path:
        window = max(1, int(summary_window))
        tail_slice = slice(max(0, len(tick_ms_series) - window), len(tick_ms_series))
        summary = {
            "steps": steps,
            "seed": config.seed,
            "log_format": log_mode,
            "deterministic_log": deterministic_log,
            "tick_ms": _summary_stats(tick_ms_series),
            "population": _summary_stats([float(v) for v in population_series]),
            "neighbor_checks": _summary_stats([float(v) for v in neighbor_checks_series]),
            "neighbor_checks_per_agent": _summary_stats(neighbor_checks_per_agent_series),
            "correlations": {
                "tick_ms_vs_neighbor_checks": _correlation(
                    tick_ms_series, [float(v) for v in neighbor_checks_series]
                ),
                "tick_ms_vs_population": _correlation(tick_ms_series, [float(v) for v in population_series]),
            },
            "over_threshold": {
                "tick_ms_gt_20": sum(1 for value in tick_ms_series if value > 20.0),
                "tick_ms_gt_30": sum(1 for value in tick_ms_series if value > 30.0),
                "tick_ms_gt_40": sum(1 for value in tick_ms_series if value > 40.0),
            },
            "peaks": {
                "tick_ms": {"value": float(max_tick_ms[0]), "tick": max_tick_ms[1]},
                "population": {"value": max_population[0], "tick": max_population[1]},
                "neighbor_checks": {"value": max_neighbor_checks[0], "tick": max_neighbor_checks[1]},
            },
            "tail_window": {
                "window": window,
                "tick_ms": _summary_stats(tick_ms_series[tail_slice]),
                "population": _summary_stats([float(v) for v in population_series[tail_slice]]),
                "neighbor_checks": _summary_stats([float(v) for v in neighbor_checks_series[tail_slice]]),
            },
        }
        Path(summary_path).write_text(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Headless terrarium simulation")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--log", type=Path, default=None, help="CSV file to write metrics")
    parser.add_argument(
        "--log-format",
        choices=["basic", "detailed"],
        default="detailed",
        help="CSV format to write when --log is provided (basic keeps legacy columns).",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=None,
        help="Optional JSON file to write summary stats for the run.",
    )
    parser.add_argument(
        "--summary-window",
        type=int,
        default=5000,
        help="Tail window size (ticks) for summary stats.",
    )
    parser.add_argument(
        "--deterministic-log",
        action="store_true",
        help="Write deterministic CSV (tick_ms is forced to 0.000 so identical seeds match).",
    )
    args = parser.parse_args()
    run_headless(
        args.steps,
        args.seed,
        args.log,
        deterministic_log=args.deterministic_log,
        log_format=args.log_format,
        summary_path=args.summary,
        summary_window=args.summary_window,
    )


if __name__ == "__main__":
    main()

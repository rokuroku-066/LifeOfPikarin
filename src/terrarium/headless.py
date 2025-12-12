from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Optional

from .config import SimulationConfig
from .world import World


def run_headless(steps: int, seed: Optional[int], log_path: Optional[Path]) -> None:
    config = SimulationConfig()
    if seed is not None:
        config.seed = seed
    world = World(config)
    writer = None
    csv_file = None
    if log_path:
        csv_file = Path(log_path).open("w", newline="")
        writer = csv.writer(csv_file)
        writer.writerow(["tick", "population", "births", "deaths", "avg_energy", "avg_age", "groups", "neighbor_checks", "tick_ms"])

    for tick in range(steps):
        metrics = world.step(tick)
        if writer:
            writer.writerow(
                [
                    metrics.tick,
                    metrics.population,
                    metrics.births,
                    metrics.deaths,
                    f"{metrics.average_energy:.4f}",
                    f"{metrics.average_age:.4f}",
                    metrics.groups,
                    metrics.neighbor_checks,
                    f"{metrics.tick_duration_ms:.3f}",
                ]
            )
    if csv_file:
        csv_file.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Headless terrarium simulation")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--log", type=Path, default=None, help="CSV file to write metrics")
    args = parser.parse_args()
    run_headless(args.steps, args.seed, args.log)


if __name__ == "__main__":
    main()

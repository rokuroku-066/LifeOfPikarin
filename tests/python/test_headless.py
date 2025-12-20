import csv
import json

import pytest

from terrarium.headless import run_headless


def _read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.reader(handle))


def test_headless_basic_log_header(tmp_path):
    log_path = tmp_path / "basic.csv"
    run_headless(steps=2, seed=1, log_path=log_path, deterministic_log=True, log_format="basic")
    rows = _read_csv(log_path)
    assert len(rows) == 3
    assert rows[0] == [
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


def test_headless_detailed_log_header_and_ratios(tmp_path):
    log_path = tmp_path / "detailed.csv"
    run_headless(steps=3, seed=2, log_path=log_path, deterministic_log=True, log_format="detailed")
    rows = _read_csv(log_path)
    assert len(rows) == 4
    header = rows[0]
    assert header == [
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

    first_row = rows[1]
    idx = {name: i for i, name in enumerate(header)}
    population = int(first_row[idx["population"]])
    births = int(first_row[idx["births"]])
    deaths = int(first_row[idx["deaths"]])
    neighbor_checks = int(first_row[idx["neighbor_checks"]])
    ungrouped = int(first_row[idx["ungrouped"]])
    tick_ms = float(first_row[idx["tick_ms"]])

    ungrouped_ratio = float(first_row[idx["ungrouped_ratio"]])
    births_per_agent = float(first_row[idx["births_per_agent"]])
    deaths_per_agent = float(first_row[idx["deaths_per_agent"]])
    neighbor_checks_per_agent = float(first_row[idx["neighbor_checks_per_agent"]])
    tick_ms_per_agent = float(first_row[idx["tick_ms_per_agent"]])

    expected_ratio = 0.0 if population == 0 else ungrouped / population
    expected_births = 0.0 if population == 0 else births / population
    expected_deaths = 0.0 if population == 0 else deaths / population
    expected_neighbors = 0.0 if population == 0 else neighbor_checks / population
    expected_tick_ms = 0.0 if population == 0 else tick_ms / population

    assert ungrouped_ratio == pytest.approx(expected_ratio, abs=1e-4)
    assert births_per_agent == pytest.approx(expected_births, abs=1e-4)
    assert deaths_per_agent == pytest.approx(expected_deaths, abs=1e-4)
    assert neighbor_checks_per_agent == pytest.approx(expected_neighbors, abs=1e-4)
    assert tick_ms_per_agent == pytest.approx(expected_tick_ms, abs=1e-4)
    assert tick_ms == 0.0


def test_headless_summary_output(tmp_path):
    log_path = tmp_path / "summary.csv"
    summary_path = tmp_path / "summary.json"
    run_headless(
        steps=4,
        seed=3,
        log_path=log_path,
        deterministic_log=True,
        log_format="basic",
        summary_path=summary_path,
        summary_window=2,
    )
    payload = json.loads(summary_path.read_text())
    assert payload["steps"] == 4
    assert payload["seed"] == 3
    assert payload["log_format"] == "basic"
    assert "tick_ms" in payload
    assert "population" in payload
    assert "neighbor_checks" in payload
    assert payload["tail_window"]["window"] == 2

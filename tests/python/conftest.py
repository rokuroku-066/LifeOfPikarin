import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
src_root = ROOT / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-config-tests",
        action="store_true",
        default=False,
        help="run tests that are intended only for configuration changes",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "config_change: marks tests that should only run when configuration files change",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-config-tests"):
        return

    skip_marker = pytest.mark.skip(
        reason="Run only when configuration is modified (use --run-config-tests)",
    )

    for item in items:
        if "config_change" in item.keywords:
            item.add_marker(skip_marker)

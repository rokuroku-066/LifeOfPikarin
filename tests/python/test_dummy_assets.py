from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_generate_dummy_assets(tmp_path: Path) -> None:
    script_path = Path("scripts/generate_dummy_assets.py")
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Generated dummy assets" in result.stdout

    expected = {
        "pikarin.glb",
        "ground.png",
        "wall_back.png",
        "wall_side.png",
    }
    assert expected.issubset({p.name for p in tmp_path.iterdir()})

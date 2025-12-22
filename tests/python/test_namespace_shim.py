import os
import subprocess
import sys
from pathlib import Path


def test_repo_imports_without_editable_install():
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    proc = subprocess.run(
        [sys.executable, "-c", "import terrarium.headless; print(terrarium.headless.__file__)"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr

    stdout = proc.stdout.strip().splitlines()
    stdout = stdout[-1] if stdout else ""
    assert stdout, "terrarium.headless path not printed"

    output_path = Path(stdout).resolve()
    expected_path = (repo_root / "src" / "terrarium" / "headless.py").resolve()
    assert output_path.samefile(expected_path)

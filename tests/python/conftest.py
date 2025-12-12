import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
python_src = ROOT / "src" / "python"
if str(python_src) not in sys.path:
    sys.path.insert(0, str(python_src))

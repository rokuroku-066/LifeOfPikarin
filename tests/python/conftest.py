import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src_dir = ROOT / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src_root = ROOT / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

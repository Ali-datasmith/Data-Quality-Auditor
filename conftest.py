import sys
from pathlib import Path

# Add src/ to sys.path for test runner discovery
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

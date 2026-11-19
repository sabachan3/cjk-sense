"""Make the service libraries importable in tests the same way the CLI does."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for service in ("detect", "fonts", "snapshot", "check"):
    sys.path.insert(0, str(ROOT / "services" / service))
sys.path.insert(0, str(ROOT))

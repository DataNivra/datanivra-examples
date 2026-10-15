"""Make ``orders_app`` importable (the repository runs pytest with ``--import-mode=importlib``)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

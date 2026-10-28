from __future__ import annotations

from pathlib import Path
import sys

# Ensure repository root is on sys.path so 'app' package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ui.app import main

if __name__ == "__main__":
    main()


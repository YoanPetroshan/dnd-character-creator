"""Test configuration - set up paths for chargen integration tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add skills/dnd/scripts to sys.path so modules like paths, library, etc. can be imported
repo_root = Path(__file__).resolve().parent.parent
scripts_dir = repo_root / "skills" / "dnd" / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

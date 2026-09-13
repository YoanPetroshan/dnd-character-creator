"""Entry point for `python -m chargen ...` — delegates to chargen.cli."""

import sys

from chargen.cli import main

if __name__ == "__main__":
    sys.exit(main())

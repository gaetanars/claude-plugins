"""Run a part script as __main__, then exit non-zero if a check() reported issues.

Usage: python -m fdm_tools.run <part.py> [args...]  (launched by fdm-run)
"""

import runpy
import sys

from fdm_tools.check import RESULTS


def main():
    piece = sys.argv[1]
    sys.argv = [piece, *sys.argv[2:]]
    try:
        runpy.run_path(piece, run_name="__main__")
    except SystemExit as e:
        if e.code not in (None, 0):
            raise
    if not RESULTS:
        sys.exit("aucun check() appelé : la pièce n'est pas vérifiée")
    sys.exit(1 if any(RESULTS) else 0)


if __name__ == "__main__":
    main()

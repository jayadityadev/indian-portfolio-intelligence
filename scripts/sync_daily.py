"""Daily incremental sync: append new trading days to the parquet cache.

Owner: Chirag.

Checks the last date in each symbol's parquet, fetches only newer rows, appends,
and updates the manifest hash. Safe to re-run; idempotent.

Run:  make sync
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError(
        "Daily sync not implemented yet. See app/data/cache.py + sources.py and "
        "docs/IMPLEMENTATION_PLAN.md §9.2 + §17 T1."
    )


if __name__ == "__main__":
    main()

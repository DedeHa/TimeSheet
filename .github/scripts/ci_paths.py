"""Resolve the CI dataset output directory (PRO-379).

The CI-timing workflow runs its producer scripts inside the `ci-metrics`
worktree (`cd metrics`), so the JSON payloads must land inside that worktree
to be committed to the `ci-metrics` branch. Resolving the output directory
relative to the current working directory (optionally overridden through the
``CI_DATA_DIR`` environment variable) keeps the producers worktree-relative
and therefore makes the publish workflow's copy paths deterministic.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DATA_SUBDIR = Path("docs") / "data"


def resolve_data_dir(explicit: str | Path | None = None) -> Path:
    """Resolve the JSON dataset output directory.

    Resolution order:
      1. ``CI_DATA_DIR`` environment variable (explicit override).
      2. ``<current working directory>/docs/data`` — the worktree-relative
         default that makes the CI-timing workflow write into the
         ``ci-metrics`` worktree instead of the master checkout.
    """
    override = explicit or os.environ.get("CI_DATA_DIR")
    if override:
        return Path(override)
    return Path.cwd() / DEFAULT_DATA_SUBDIR

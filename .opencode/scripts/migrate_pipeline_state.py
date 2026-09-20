#!/usr/bin/env python3
"""Migrate pipeline state from home directory to project-local .opencode directory.

This script moves ``pipeline-state.json`` and ``pipeline-history.json`` from
the legacy ``~/.opencode/`` location to the project-local ``.opencode/``
directory. It is idempotent, atomic, and makes no schema changes.

Usage:
    python migrate_pipeline_state.py
    python migrate_pipeline_state.py --show
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

OLD_STATE_PATH = Path.home() / ".opencode" / "pipeline-state.json"
OLD_HISTORY_PATH = Path.home() / ".opencode" / "pipeline-history.json"


def _new_state_path() -> Path:
    """Return the project-local pipeline state path."""
    return Path(__file__).resolve().parent.parent / "pipeline-state.json"


def _new_history_path() -> Path:
    """Return the project-local pipeline history path."""
    return Path(__file__).resolve().parent.parent / "pipeline-history.json"


def _load_json(path: Path) -> dict | None:
    """Load a JSON file as a dict, returning None if missing or invalid."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        logger.warning("Invalid JSON at %s, skipping", path)
        return None


def _save_json_atomic(path: Path, data: dict) -> None:
    """Persist a dict to JSON atomically via temp-file rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    tmp.replace(path)


def migrate_pipeline_state(state_path: Path | None = None) -> dict:
    """Migrate pipeline state files from old home location to project-local .opencode.

    Handles four cases:
    - **Old-only**: copies state from old to new location.
    - **Both exist**: merges with new taking precedence; logs merged keys.
    - **Neither**: no action.
    - **Idempotent**: safe to run multiple times.

    Args:
        state_path: Optional override for new state path (used in tests).

    Returns a summary dict with ``state_merged_keys`` and
    ``history_merged_keys``.
    """
    new_state_path = state_path if state_path is not None else _new_state_path()
    new_history_path = (
        Path(
            str(new_state_path).replace("pipeline-state.json", "pipeline-history.json")
        )
        if state_path is not None
        else _new_history_path()
    )

    state_merged_keys: list[str] = []
    history_merged_keys: list[str] = []

    old_state = _load_json(OLD_STATE_PATH)
    new_state = _load_json(new_state_path)

    if old_state is not None and new_state is None:
        _save_json_atomic(new_state_path, old_state)
        logger.info(
            "Migrated pipeline state from %s to %s",
            OLD_STATE_PATH,
            new_state_path,
        )
    elif old_state is not None and new_state is not None:
        merged = {**old_state, **new_state}
        state_merged_keys = [k for k in old_state if k in new_state]
        _save_json_atomic(new_state_path, merged)
        logger.info(
            "Merged pipeline state from old and new locations; merged keys: %s",
            state_merged_keys,
        )

    old_history = _load_json(OLD_HISTORY_PATH)
    new_history = _load_json(new_history_path)

    if old_history is not None and new_history is None:
        _save_json_atomic(new_history_path, old_history)
        logger.info(
            "Migrated pipeline history from %s to %s",
            OLD_HISTORY_PATH,
            new_history_path,
        )
    elif old_history is not None and new_history is not None:
        merged = {**old_history, **new_history}
        history_merged_keys = [k for k in old_history if k in new_history]
        _save_json_atomic(new_history_path, merged)
        logger.info(
            "Merged pipeline history from old and new locations; merged keys: %s",
            history_merged_keys,
        )

    return {
        "state_merged_keys": state_merged_keys,
        "history_merged_keys": history_merged_keys,
    }


def main() -> int:
    """Run pipeline state migration and print a JSON summary."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = migrate_pipeline_state()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

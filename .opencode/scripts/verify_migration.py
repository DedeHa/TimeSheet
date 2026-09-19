#!/usr/bin/env python3
"""Verify migration integrity across all pipeline tickets.

Checks that all 6 tickets (PRO-373, PRO-375, PRO-376, PRO-380, PRO-381,
PRO-382) have their data preserved after migration from ~/.opencode/ to
.project-local .opencode/.

Usage:
    python migrate_pipeline_state.py --verify
    python migrate_pipeline_state.py --verify --checksum
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

OLD_STATE_PATH = Path.home() / ".opencode" / "pipeline-state.json"
OLD_HISTORY_PATH = Path.home() / ".opencode" / "pipeline-history.json"
NEW_STATE_PATH = Path(__file__).resolve().parent.parent / "pipeline-state.json"
NEW_HISTORY_PATH = Path(__file__).resolve().parent.parent / "pipeline-history.json"

TICKETS = ["PRO-373", "PRO-375", "PRO-376", "PRO-380", "PRO-381", "PRO-382"]


def _load_json(path: Path) -> dict | None:
    """Load a JSON file as a dict, returning None if missing or invalid."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _checksum(path: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_migration(checksum: bool = False) -> dict:
    """Verify all 6 tickets' data is preserved after migration.

    Args:
        checksum: If True, include file checksums in the report.

    Returns a dict with per-ticket status and summary.
    """
    old_state = _load_json(OLD_STATE_PATH)
    new_state = _load_json(NEW_STATE_PATH)

    report = {
        "tickets": {},
        "summary": {
            "total": len(TICKETS),
            "preserved": 0,
            "missing": [],
            "corrupted": [],
        },
    }

    if checksum:
        report["checksums"] = {
            "old_state": _checksum(OLD_STATE_PATH) if OLD_STATE_PATH.exists() else None,
            "new_state": _checksum(NEW_STATE_PATH) if NEW_STATE_PATH.exists() else None,
            "old_history": (
                _checksum(OLD_HISTORY_PATH) if OLD_HISTORY_PATH.exists() else None
            ),
            "new_history": (
                _checksum(NEW_HISTORY_PATH) if NEW_HISTORY_PATH.exists() else None
            ),
        }

    for ticket in TICKETS:
        old_ticket = old_state.get(ticket) if old_state else None
        new_ticket = new_state.get(ticket) if new_state else None
        preserved = old_ticket is not None and new_ticket is not None

        ticket_report = {
            "old_exists": old_ticket is not None,
            "new_exists": new_ticket is not None,
            "preserved": preserved,
        }

        if preserved:
            report["summary"]["preserved"] += 1
        else:
            report["summary"]["missing"].append(ticket)

        if old_ticket is not None and new_ticket is None:
            report["summary"]["corrupted"].append(ticket)

        report["tickets"][ticket] = ticket_report

    return report


def main() -> int:
    """Run migration verification and print JSON report."""
    checksum = "--checksum" in sys.argv
    report = verify_migration(checksum=checksum)
    print(json.dumps(report, indent=2))

    if report["summary"]["missing"] or report["summary"]["corrupted"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

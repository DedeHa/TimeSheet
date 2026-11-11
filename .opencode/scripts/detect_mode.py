#!/usr/bin/env python3
"""Detect and persist the development mode for a pipeline ticket.

Usage:
    python detect_mode.py <ticket> "<chat message>"
    python detect_mode.py <ticket> --show

Reads/writes ``~/.opencode/pipeline-state.json``.  The Product Owner agent
invokes this script to parse user chat messages for mode keywords and to
read back the persisted mode before each handoff.

For advanced pipeline management (resume, continue, what-missed, dry-run,
check-stuck, history, reset), use:

    python pipeline.py <command> <ticket> [options]

See pipeline.py --help for all available commands.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

STATE_PATH = Path.home() / ".opencode" / "pipeline-state.json"

# The state file is shared with pipeline.py, so the fail-closed reader and the atomic
# writer live there. pipeline.py sits next to this file and is loaded by path, so the
# script works from any working directory (PRO-407, F1).
_PIPELINE_PATH = Path(__file__).resolve().parent / "pipeline.py"


def _load_pipeline() -> ModuleType:
    """Load pipeline.py from this script's directory and return the module."""
    spec = importlib.util.spec_from_file_location("pipeline_shared", _PIPELINE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {_PIPELINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_pipeline = _load_pipeline()
StateFileError = _pipeline.StateFileError

# Conversational phrases that indicate the user wants no pauses during development.
AUTOMATED_PATTERNS = (
    re.compile(r"\brun in automated\b", re.IGNORECASE),
    re.compile(r"\brun automated\b", re.IGNORECASE),
    re.compile(r"\brun in automated mode\b", re.IGNORECASE),
    re.compile(r"\brun automated mode\b", re.IGNORECASE),
    re.compile(r"\bautomated mode\b", re.IGNORECASE),
    re.compile(r"\bautomated\b", re.IGNORECASE),
    re.compile(r"\bno pauses?\b", re.IGNORECASE),
    re.compile(r"\bdirect dispatch\b", re.IGNORECASE),
    re.compile(r"\bjust run it\b", re.IGNORECASE),
    re.compile(r"\bkeep going\b", re.IGNORECASE),
    re.compile(r"\bwithout confirmation\b", re.IGNORECASE),
    re.compile(r"\bwithout pauses?\b", re.IGNORECASE),
    re.compile(r"\bgo straight\b", re.IGNORECASE),
    re.compile(r"\bno questions\b", re.IGNORECASE),
)

INTERACTIVE_PATTERNS = (
    re.compile(r"\brun in interactive\b", re.IGNORECASE),
    re.compile(r"\brun interactive\b", re.IGNORECASE),
    re.compile(r"\brun in interactive mode\b", re.IGNORECASE),
    re.compile(r"\brun interactive mode\b", re.IGNORECASE),
    re.compile(r"\binteractive mode\b", re.IGNORECASE),
    re.compile(r"\binteractive\b", re.IGNORECASE),
    re.compile(r"\bpause\b", re.IGNORECASE),
    re.compile(r"\bconfirm\b", re.IGNORECASE),
    re.compile(r"\bask me\b", re.IGNORECASE),
    re.compile(r"\bstop between\b", re.IGNORECASE),
    re.compile(r"\bstop between steps\b", re.IGNORECASE),
    re.compile(r"\bconfirm before\b", re.IGNORECASE),
    re.compile(r"\bask before\b", re.IGNORECASE),
)

# Conversational hints that lean towards automated but are not definitive.
AUTOMATED_HINTS = (
    re.compile(r"\bgo ahead\b", re.IGNORECASE),
    re.compile(r"\bproceed\b", re.IGNORECASE),
    re.compile(r"\bskip the pause\b", re.IGNORECASE),
    re.compile(r"\bskip confirmation\b", re.IGNORECASE),
    re.compile(r"\bjust do it\b", re.IGNORECASE),
    re.compile(r"\bno need to ask\b", re.IGNORECASE),
)


def _load_state() -> dict:
    """Return the pipeline state file, or {} when it does not exist.

    Reads never create the directory. Raises StateFileError for corrupt content, so the
    caller exits 1 and the file stays byte-identical.
    """
    return _pipeline._read_json_object(STATE_PATH)


def _save_state(state: dict) -> None:
    """Persist the pipeline state file through pipeline.py's atomic writer.

    The directory is created here, on write only.
    """
    _pipeline._write_json_atomic(STATE_PATH, state)


def detect_mode(message: str) -> dict:
    """Parse a chat message for mode keywords.

    Returns a dict with ``mode``, ``confidence`` and ``matched`` keys.
    ``mode`` is ``"automated"``, ``"interactive"`` or ``None``.
    ``confidence`` is ``"high"`` or ``"low"`` depending on how specific
    the keyword match was. ``matched`` is the phrase that triggered the
    detection, or ``None``.
    """
    if not message:
        return {"mode": None, "confidence": None, "matched": None}

    for pattern in AUTOMATED_PATTERNS:
        m = pattern.search(message)
        if m:
            return {"mode": "automated", "confidence": "high", "matched": m.group(0)}

    for pattern in INTERACTIVE_PATTERNS:
        m = pattern.search(message)
        if m:
            return {"mode": "interactive", "confidence": "high", "matched": m.group(0)}

    # Conversational hints that are not definitive but lean towards automated
    # (e.g. "go ahead", "proceed", "skip the pauses").
    for pattern in AUTOMATED_HINTS:
        m = pattern.search(message)
        if m:
            return {"mode": "automated", "confidence": "low", "matched": m.group(0)}

    return {"mode": None, "confidence": None, "matched": None}


def format_mode_result(result: dict) -> str:
    """Format the result of detect_mode as a human-readable string."""
    if result["mode"] is None:
        return "No mode detected"
    return (
        f"Mode: {result['mode']} (confidence: {result['confidence']}, "
        f"matched: '{result['matched']}')"
    )


def set_mode(ticket: str, mode: str) -> dict:
    """Persist ``mode`` for ``ticket`` and return the updated entry."""
    state = _load_state()
    entry = state.get(ticket, {})
    entry["development_mode"] = mode
    entry["last_updated"] = datetime.now(timezone.utc).isoformat()
    state[ticket] = entry
    _save_state(state)
    return entry


def get_mode(ticket: str) -> str:
    """Return the persisted mode for ``ticket`` (default ``interactive``)."""
    state = _load_state()
    entry = state.get(ticket, {})
    mode = entry.get("development_mode")
    if mode not in ("interactive", "automated"):
        return "interactive"
    return mode


def main() -> int:
    """Detect and persist the development mode for a pipeline ticket.

    Parses ``sys.argv`` for a ticket key and an optional chat message.
    With ``--show`` reads the persisted mode; otherwise writes the
    detected mode to the pipeline state file and prints the result.
    A corrupt state file is reported on stderr and exits 1 without modification.
    """
    parser = argparse.ArgumentParser(description="Detect and persist pipeline mode")
    parser.add_argument("ticket", help="JIRA ticket key, e.g. PRO-373")
    parser.add_argument(
        "message",
        nargs="?",
        default="",
        help="Chat message to parse for mode keywords",
    )
    parser.add_argument("--show", action="store_true", help="Show persisted mode")
    args = parser.parse_args()

    try:
        if args.show:
            print(get_mode(args.ticket))
            return 0

        result = detect_mode(args.message)
        if result["mode"] is None:
            print(f"No mode detected; current mode: {get_mode(args.ticket)}")
            return 0

        entry = set_mode(args.ticket, result["mode"])
    except StateFileError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    print(format_mode_result(result))
    print(json.dumps(entry, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

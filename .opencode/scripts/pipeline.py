#!/usr/bin/env python3
"""Enhanced pipeline management tool for TimeSheetAlgo agent team.

This tool provides commands to:
- Resume/continue/proceed pipeline steps that are stuck
- Show what work was missed in interrupted pipelines
- Preview pipeline actions (dry-run)
- Detect and alert on stuck pipelines
- Manage pipeline history and transitions
- Record agent handoffs and render the JIRA handoff comment (FR-25)

Recovery commands implement FR-22. Handoff recording implements FR-25.

Usage:
    python pipeline.py <command> <ticket> [options]

Commands:
    show state <ticket>              Show current pipeline state (read-only)
    resume <ticket>                   Resume pipeline at current step (--force clears a block)
    interrupt <ticket> [--reason]     Mark a pipeline interrupted until it is resumed
    continue <ticket>                 Continue to next pipeline step (--force bypasses the handoff rule, never the DoR gate)
    proceed <ticket>                  Proceed with current step execution
    what-missed <ticket>              Show what work was missed in interrupted pipeline (read-only)
    dry-run <ticket> <command>        Preview action without executing (read-only)
    check-stuck <ticket>              Detect and alert on stuck pipelines (read-only)
    reset <ticket>                    Reset all cycles and state
    history <ticket>                  Show pipeline history (read-only)
    set-mode <ticket> <mode>           Set interactive/automated mode
    get-mode <ticket>                  Show persisted mode (read-only)
    dor <ticket> [--json ...]         Record or show the Definition of Ready checklist (D1-D7)
    waive <ticket> <DOR_ID>           Waive one DoR item (--reason and --by required)
    reconcile <ticket> [--base B]     Check changed areas have their living documents
    handoff <ref> --from --to ...     Record a handoff and print its comment (any work item ref)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

STATE_PATH = Path.home() / ".opencode" / "pipeline-state.json"
HISTORY_PATH = Path.home() / ".opencode" / "pipeline-history.json"

STEP_ORDER = ["plan", "develop", "complete"]
# An in_progress step with no update for this many hours counts as interrupted (FR-22).
INTERRUPT_AFTER_HOURS = 24
JIRA_REF_PATTERN = re.compile(r"[A-Z][A-Z0-9]+-\d+")
GITHUB_ISSUE_PATTERN = re.compile(r"(?:GH-\d+|[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#\d+)")
GENERIC_REF_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")

HANDOFF_STATUSES = ("COMPLETED", "BLOCKED", "IN_PROGRESS")
DOR_IDS = ("D1", "D2", "D3", "D4", "D5", "D6", "D7")
DOR_VALUES = ("pass", "fail")
ROOT = Path(__file__).resolve().parents[2]

# Changed area -> (path prefixes, living documents that must move with it).
# Mirrors the table in complete-feature Step 4.5 (PRO-407, AC-4).
RECONCILE_RULES: Tuple[Tuple[Tuple[str, ...], str, Tuple[str, ...]], ...] = (
    (("src/",), "application code (src/)",
     ("docs/ARCHITECTURE.md", "docs/REQUIREMENTS.md")),
    (("tests/", ".opencode/tests/"), "tests",
     ("docs/TESTING.md",)),
    ((".opencode/scripts/", ".opencode/skills/", ".opencode/agents/"),
     "agent team (.opencode scripts, skills, agents)",
     ("AGENTS.md", "docs/CONTRIBUTING.md")),
)


def changed_files(base: str, cwd: Optional[Path] = None) -> List[str]:
    """Return the files changed on HEAD relative to base (git diff --name-only base...HEAD).

    Raises RuntimeError when git is missing, the directory is not a repository, or the
    base ref does not exist, so callers can report the problem instead of crashing.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(str(exc)) from exc
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git diff exited {result.returncode}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def parse_work_item_ref(ref: str) -> Dict[str, str]:
    """Classify a work item reference as jira, github, or generic (PRO-407, Step 6).

    - jira: an uppercase project key and a number, e.g. PRO-123 or ABC-9
    - github: GH-456 or owner/repo#456
    - generic: any other identifier that starts with a letter, e.g. feat-login

    Surrounding whitespace is ignored. Raises ValueError for empty, non-string, or
    malformed references.
    """
    if not isinstance(ref, str):
        raise ValueError("work item reference must be a string")
    value = ref.strip()
    if not value:
        raise ValueError("work item reference must not be empty")
    if GITHUB_ISSUE_PATTERN.fullmatch(value):
        return {"tracker": "github", "key": value}
    if JIRA_REF_PATTERN.fullmatch(value):
        return {"tracker": "jira", "key": value}
    if GENERIC_REF_PATTERN.fullmatch(value):
        return {"tracker": "generic", "key": value}
    raise ValueError(f"invalid work item reference: {ref!r}")


def _utc_now() -> datetime:
    """Return the current time in UTC. Tests pass an explicit `now` instead."""
    return datetime.now(timezone.utc)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp as an aware UTC datetime, or None when unreadable."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def interruption_reason(entry: Dict[str, Any], now: datetime) -> Optional[str]:
    """Return why a pipeline entry counts as interrupted, or None (PRO-407, AC-2).

    The single definition, shared by show, what-missed, check-stuck, dry-run and resume:
    - the pipeline is BLOCKED by a handoff, or
    - an operator marked it interrupted (the `interrupt` command; `resume` clears it), or
    - the status is in_progress, the step has not been reported complete, and nothing
      was recorded for INTERRUPT_AFTER_HOURS. A fresh in_progress step (for example just
      after `continue`) is not interrupted, and neither is a step whose COMPLETED
      handoff is waiting for `continue`.
    """
    if entry.get("blocked") or entry.get("status") == "blocked":
        return "blocked by a handoff"
    if entry.get("interrupted"):
        return "marked interrupted"
    if entry.get("status") == "in_progress" and not entry.get("step_reported_complete"):
        stamp = _parse_timestamp(entry.get("last_updated"))
        if stamp is None or now - stamp > timedelta(hours=INTERRUPT_AFTER_HOURS):
            return f"in progress with no update for over {INTERRUPT_AFTER_HOURS} hours"
    return None


def _normalise_path(path: str) -> str:
    """Use forward slashes and drop a leading ./ so prefixes match."""
    cleaned = path.replace("\\", "/")
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned


def find_reconciliation_gaps(changed: Iterable[str]) -> List[Tuple[str, Tuple[str, ...]]]:
    """Return (area label, required documents) for each changed area with no living-doc change."""
    paths = {_normalise_path(path) for path in changed if path}
    gaps: List[Tuple[str, Tuple[str, ...]]] = []
    for prefixes, label, documents in RECONCILE_RULES:
        touched = any(path.startswith(prefix) for path in paths for prefix in prefixes)
        if touched and not any(document in paths for document in documents):
            gaps.append((label, documents))
    return gaps


class StateFileError(RuntimeError):
    """A state or history file exists but is not a readable JSON object (PRO-407, FR-22).

    The tool fails closed: it reports this error, exits 1, and never rewrites the file.
    """


def _read_json_object(path: Path) -> Dict[str, Any]:
    """Return the JSON object stored at path, or {} when the file does not exist.

    Raises StateFileError for unreadable, non-JSON, or non-object content. Nothing is
    written, so a corrupt file stays byte-identical for inspection.
    """
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StateFileError(
            f"{path} is not readable JSON ({exc}). It was not modified. "
            "Move or repair the file, then retry."
        ) from exc
    if not isinstance(data, dict):
        raise StateFileError(
            f"{path} must contain a JSON object. It was not modified. "
            "Move or repair the file, then retry."
        )
    return data


class PipelineManager:
    """Enhanced pipeline management with resume/continue/proceed functionality."""

    def __init__(self):
        self.state = self._load_state()
        self.history = self._load_history()

    def _load_state(self) -> Dict[str, Any]:
        """Load the pipeline state file (fails closed on corrupt content)."""
        return _read_json_object(STATE_PATH)

    def _save_state(self) -> None:
        """Persist the pipeline state file atomically."""
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.state, fh, indent=2, sort_keys=True)
        tmp.replace(STATE_PATH)

    def _load_history(self) -> Dict[str, Any]:
        """Load the pipeline history file (fails closed on corrupt content)."""
        return _read_json_object(HISTORY_PATH)

    def _save_history(self) -> None:
        """Persist the pipeline history file atomically."""
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = HISTORY_PATH.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.history, fh, indent=2, sort_keys=True)
        tmp.replace(HISTORY_PATH)

    @staticmethod
    def _default_entry() -> Dict[str, Any]:
        """Return the initial state entry for a new ticket."""
        return {
            "development_mode": "interactive",
            "current_step": "plan",
            "cycle_counts": {"plan": 0, "develop": 0, "complete": 0},
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "status": "not_started",
            "blocked": False,
            "escalation_level": 0,
        }

    def _get_entry(self, ticket: str) -> Dict[str, Any]:
        """Get or create a pipeline entry for a ticket (write paths only)."""
        if ticket not in self.state:
            self.state[ticket] = self._default_entry()
            self._save_state()
            self._record_history(ticket, "pipeline_created", self.state[ticket])
        return self.state[ticket]

    def _peek_entry(self, ticket: str) -> Dict[str, Any]:
        """Return a ticket entry for a read path without creating or persisting it (FR-22).

        Unknown tickets get a default entry that is not stored, so read-only commands
        leave the state and history files untouched.
        """
        if ticket in self.state:
            return self.state[ticket]
        return self._default_entry()

    def _record_history(self, ticket: str, action: str, details: Dict[str, Any]) -> None:
        """Record pipeline state change in history."""
        timestamp = datetime.now(timezone.utc).isoformat()
        if ticket not in self.history:
            self.history[ticket] = {
                "created": timestamp,
                "actions": [],
                "transitions": []
            }
        self.history[ticket]["actions"].append({
            "timestamp": timestamp,
            "action": action,
            "details": details
        })
        self.history[ticket]["last_updated"] = timestamp
        self._save_history()

    def _detect_interruption(
        self, ticket: str, now: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Return what was missed when the pipeline is interrupted, else None.

        Interruption is defined once, in interruption_reason(). `now` is injectable so
        tests can use a fixed clock.
        """
        entry = self._peek_entry(ticket)
        reason = interruption_reason(entry, now or _utc_now())
        if reason is None:
            return None
        current_step = entry.get("current_step")
        return {
            "interrupted": True,
            "reason": reason,
            "interrupted_step": current_step,
            "interrupted_at": entry.get("last_updated"),
            "what_was_missed": self._get_missed_work(ticket, entry),
        }

    def _get_missed_work(self, ticket: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Determine what work was missed in an interrupted pipeline."""
        current_step = entry.get("current_step")
        cycle_counts = entry.get("cycle_counts", {})
        
        # Map steps to expected work
        step_expectations = {
            "plan": {
                "expected_cycles": 1,
                "expected_work": "Architecture plan with implementation plan (Part A/B/C)",
                "current_cycles": cycle_counts.get("plan", 0)
            },
            "develop": {
                "expected_cycles": 1,
                "expected_work": "Implementation with rollout steps completed",
                "current_cycles": cycle_counts.get("develop", 0)
            },
            "complete": {
                "expected_cycles": 1,
                "expected_work": "Testing with validation and JIRA closure",
                "current_cycles": cycle_counts.get("complete", 0)
            }
        }
        
        expectation = step_expectations.get(current_step, {})
        
        return {
            "step": current_step,
            "expected_cycles": expectation.get("expected_cycles", 1),
            "current_cycles": expectation.get("current_cycles", 0),
            "expected_work": expectation.get("expected_work", "Unknown work"),
            "work_status": "INCOMPLETE" if expectation.get("current_cycles", 0) == 0 else "COMPLETE"
        }

    def show_state(self, ticket: str, now: Optional[datetime] = None) -> None:
        """Show current pipeline state with interruption detection."""
        entry = self._peek_entry(ticket)
        
        print(f"=== Pipeline State: {ticket} ===\n")
        
        print(f"Current Step: {entry.get('current_step', 'N/A')}")
        print(f"Status: {entry.get('status', 'N/A')}")
        print(f"Development Mode: {entry.get('development_mode', 'interactive')}")
        print(f"Last Updated: {entry.get('last_updated', 'N/A')}")
        if entry.get("blocked"):
            level = entry.get("escalation_level", 0)
            print(f"\n⛔ PIPELINE BLOCKED by a handoff (escalation level {level})")

        cycle_counts = entry.get("cycle_counts", {})
        print(f"\nCycle Counts:")
        print(f"  Plan: {cycle_counts.get('plan', 0)} (max: 3)")
        print(f"  Develop: {cycle_counts.get('develop', 0)} (max: 3)")
        print(f"  Complete: {cycle_counts.get('complete', 0)} (max: 3)")
        
        # Check for interruption
        interruption = self._detect_interruption(ticket, now)
        if interruption and interruption.get("interrupted"):
            print(f"\n⚠️  INTERRUPTED PIPELINE DETECTED!")
            print(f"   Reason: {interruption['reason']}")
            print(f"   Step: {interruption['interrupted_step']}")
            print(f"   Interrupted at: {interruption['interrupted_at']}")
            print(f"\n   What was missed:")
            missed = interruption['what_was_missed']
            print(f"   - Step: {missed['step']}")
            print(f"   - Expected cycles: {missed['expected_cycles']}")
            print(f"   - Current cycles: {missed['current_cycles']}")
            print(f"   - Expected work: {missed['expected_work']}")
            print(f"   - Status: {missed['work_status']}")
        else:
            print(f"\n✅ Pipeline is not interrupted")
        
        print(f"\nEscalation Level: {entry.get('escalation_level', 0)}")
        print(f"Blocked: {entry.get('blocked', False)}")

    def resume(self, ticket: str, force: bool = False, now: Optional[datetime] = None) -> int:
        """Resume pipeline at the current step. Returns 0 when resumed, 1 when refused.

        An interrupted or blocked pipeline needs --force. A forced resume moves the
        status to resumed, clears the block and any interrupted marker, so the pipeline
        is no longer reported as interrupted (PRO-407, AC-2).
        """
        entry = self._get_entry(ticket)
        current_step = entry.get("current_step")

        print(f"=== Resuming Pipeline: {ticket} ===\n")

        interruption = self._detect_interruption(ticket, now)
        was_interrupted = bool(interruption and interruption.get("interrupted"))
        was_blocked = bool(entry.get("blocked"))

        if was_interrupted:
            print(f"⚠️  Pipeline was interrupted at step: {interruption['interrupted_step']}")
            print(f"   Reason: {interruption['reason']}")
            print(f"   What was missed:")
            missed = interruption['what_was_missed']
            print(f"   - {missed['step']}: {missed['expected_work']}")
            print(f"   - Cycles: {missed['current_cycles']}/{missed['expected_cycles']}")
        if was_blocked:
            print(f"⛔ Pipeline is BLOCKED (escalation level {entry.get('escalation_level', 0)})")

        if was_interrupted and not force:
            print(f"\n   ⚠️  Pipeline needs to be reset or completed before resuming.")
            print(f"   Use 'reset' to clear all progress and start over.")
            print(f"   Or provide --force to skip validation.")
            return 1

        print(f"Resuming pipeline at step: {current_step}")

        if was_interrupted:
            entry["status"] = "resumed"
            entry["blocked"] = False
            entry.pop("interrupted", None)
            entry.pop("interrupted_reason", None)
            entry["last_updated"] = (now or _utc_now()).isoformat()
            self._save_state()
            self._record_history(ticket, "interruption_cleared", entry)
            print(f"   ✓ Interruption flag cleared")

        print(f"\n✅ Pipeline resumed successfully")
        return 0

    def interrupt(self, ticket: str, reason: str = "") -> int:
        """Mark the pipeline interrupted until it is resumed (FR-22).

        This is the explicit marker in interruption_reason(). `resume` clears it, and so
        does a successful `continue`.
        """
        reason = (reason or "").strip() or "marked interrupted by an operator"
        entry = self._get_entry(ticket)
        entry["interrupted"] = True
        entry["interrupted_reason"] = reason
        self._save_state()
        self._record_history(ticket, "interruption_marked", {"reason": reason})
        print(f"✓ {ticket} marked interrupted: {reason}")
        print(f"  'resume' clears the marker (use --force to resume an interrupted pipeline)")
        return 0

    def what_missed(self, ticket: str, now: Optional[datetime] = None) -> None:
        """Show what work was missed in an interrupted pipeline."""
        interruption = self._detect_interruption(ticket, now)
        if not interruption or not interruption.get("interrupted"):
            print(f"No interrupted pipeline found for {ticket}")
            entry = self._peek_entry(ticket)
            print(f"Pipeline status: {entry.get('status', 'N/A')}, but not interrupted")
            return
        
        entry = self._peek_entry(ticket)
        print(f"=== What Was Missed: {ticket} ===\n")
        
        print(f"⚠️  Pipeline interrupted at: {interruption['interrupted_at']}")
        print(f"   Reason: {interruption['reason']}")
        print(f"   Step: {interruption['interrupted_step']}\n")
        
        missed = interruption['what_was_missed']
        print(f"What was missed:")
        print(f"  Step: {missed['step']}")
        print(f"  Expected cycles: {missed['expected_cycles']}")
        print(f"  Current cycles: {missed['current_cycles']}")
        print(f"  Expected work: {missed['expected_work']}")
        print(f"  Status: {missed['work_status']}\n")
        
        if missed['current_cycles'] == 0:
            print(f"  💡 This means the {missed['step']} step was never executed.")
            print(f"  🔄 Use 'resume' to attempt to complete this step.")
            print(f"  ⚠️  If the step truly cannot be completed, use 'reset' to start over.")
        
        print(f"\nCurrent pipeline state:")
        print(f"  Step: {entry.get('current_step')}")
        print(f"  Cycles: {entry.get('cycle_counts')}")
        print(f"  Status: {entry.get('status')}")

    @staticmethod
    def _dor_missing(entry: Dict[str, Any]) -> List[str]:
        """Return the D1-D7 items that are neither pass nor waived (PRO-407, AC-3)."""
        checklist = entry.get("dor", {})
        return [dor_id for dor_id in DOR_IDS if checklist.get(dor_id) not in ("pass", "waived")]

    def record_dor(self, ticket: str, values: Any) -> Dict[str, Any]:
        """Record pass or fail for D1-D7 items. Waivers go through waive().

        Raises ValueError for unknown IDs, values other than pass or fail, or a payload
        that is not a mapping. Nothing is written when validation fails.
        """
        if not isinstance(values, dict):
            raise ValueError("DoR checklist must be a JSON object such as {\"D1\": \"pass\"}")
        cleaned: Dict[str, str] = {}
        for dor_id, value in values.items():
            if dor_id not in DOR_IDS:
                raise ValueError(
                    f"unknown DoR item {dor_id!r}; expected one of {', '.join(DOR_IDS)}"
                )
            normalised = str(value).strip().lower()
            if normalised not in DOR_VALUES:
                raise ValueError(
                    f"DoR item {dor_id} must be pass or fail "
                    f"(use 'waive' for waivers), got {value!r}"
                )
            cleaned[dor_id] = normalised

        entry = self._get_entry(ticket)
        checklist = entry.setdefault("dor", {})
        waivers = entry.setdefault("dor_waivers", {})
        for dor_id, value in cleaned.items():
            checklist[dor_id] = value
            if value == "pass":
                waivers.pop(dor_id, None)
        entry["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        self._record_history(ticket, "dor_recorded", {"values": cleaned})
        return checklist

    def waive(self, ticket: str, dor_id: str, reason: str, by: str) -> None:
        """Waive one DoR item. A non-empty reason and owner are required (PRO-407, AC-3)."""
        if dor_id not in DOR_IDS:
            raise ValueError(f"unknown DoR item {dor_id!r}; expected one of {', '.join(DOR_IDS)}")
        reason = (reason or "").strip()
        by = (by or "").strip()
        if not reason:
            raise ValueError("a waiver requires a non-empty --reason")
        if not by:
            raise ValueError("a waiver requires a non-empty --by (the waiving owner)")

        entry = self._get_entry(ticket)
        entry.setdefault("dor", {})[dor_id] = "waived"
        entry.setdefault("dor_waivers", {})[dor_id] = {
            "waiver_reason": reason,
            "waived_by": by,
        }
        entry["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        self._record_history(ticket, "dor_waiver", {"dor_id": dor_id, "waiver_reason": reason,
                                                    "waived_by": by})
        print(f"✓ {dor_id} waived for {ticket} by {by}: {reason}")

    def show_dor(self, ticket: str) -> None:
        """Print the recorded DoR checklist without changing state."""
        entry = self._peek_entry(ticket)
        checklist = entry.get("dor", {})
        waivers = entry.get("dor_waivers", {})
        print(f"=== Definition of Ready: {ticket} ===\n")
        for dor_id in DOR_IDS:
            value = checklist.get(dor_id, "missing")
            line = f"{dor_id}: {value}"
            if dor_id in waivers:
                line += f" (by {waivers[dor_id]['waived_by']}: {waivers[dor_id]['waiver_reason']})"
            print(line)
        missing = self._dor_missing(entry)
        print(f"\nGate: {'passed' if not missing else 'not passed (' + ', '.join(missing) + ')'}")

    def reconcile(
        self, ticket: str, base: str = "master", changed: Optional[Sequence[str]] = None
    ) -> int:
        """Check that every changed area has its living document in the diff (FR-24).

        Returns 0 when reconciled and 1 when a gap exists or the diff cannot be read.
        Reads only; no state or history is written.
        """
        print(f"=== Documentation Reconciliation: {ticket} ===\n")
        if changed is None:
            try:
                files = changed_files(base)
            except RuntimeError as exc:
                print(f"❌ Cannot read the diff against {base}: {exc}")
                print("   Pass --changed PATH (repeatable) to supply the changed files.")
                return 1
        else:
            files = list(changed)

        if not files:
            print(f"No changed files against {base}; nothing to reconcile.")
            return 0

        gaps = find_reconciliation_gaps(files)
        if not gaps:
            print(f"✅ Documentation reconciled for {len(files)} changed file(s).")
            return 0

        print(f"❌ {len(gaps)} changed area(s) have no living-document change in the diff:")
        for label, documents in gaps:
            print(f"   - {label}: update one of {', '.join(documents)}")
        return 1

    def _last_handoff(self, ticket: str) -> Optional[Dict[str, Any]]:
        """Return the most recent handoff recorded in the current run, if any.

        A pipeline_reset starts a new run, so handoffs before it are ignored.
        """
        for action in reversed(self.history.get(ticket, {}).get("actions", [])):
            if action.get("action") == "pipeline_reset":
                return None
            if action.get("action") == "handoff":
                return action.get("details", {})
        return None

    def _handoff_blockers(self, ticket: str, entry: Dict[str, Any]) -> List[str]:
        """Return the handoff-rule reasons the current step cannot advance (empty if none).

        These are the only reasons `--force` may bypass (PRO-407, FR-23).
        """
        current_step = entry.get("current_step")
        reasons: List[str] = []
        current_cycles = entry.get("cycle_counts", {}).get(current_step, 0)
        if current_cycles == 0:
            reasons.append(f"{current_step} has 0 completed cycles")
        last = self._last_handoff(ticket)
        if last is None:
            reasons.append("no handoff recorded for this run")
        elif str(last.get("status", "")).upper() != "COMPLETED":
            reasons.append(f"last handoff status is {last.get('status')}, not COMPLETED")
        return reasons

    def _dor_blockers(self, entry: Dict[str, Any]) -> List[str]:
        """Return the DoR reasons the develop step cannot start (empty if the gate passes).

        The DoR gate is never bypassed by --force (PRO-407, FR-23).
        """
        missing = self._dor_missing(entry)
        return [f"DoR gate not passed: {', '.join(missing)}"] if missing else []

    def continue_step(self, ticket: str, force: bool = False) -> int:
        """Advance pipeline to the next step. Returns 0 when advanced, 1 when refused.

        Two rules apply. The DoR gate (entering develop) always applies: every D1-D7
        item must be pass or waived, and --force does not override it. The handoff rule
        (the latest handoff is COMPLETED and the current step has a completed cycle) can
        be bypassed with --force, which records forced_advance and clears a BLOCKED
        state.
        """
        entry = self._get_entry(ticket)
        current_step = entry.get("current_step")

        print(f"=== Continuing Pipeline: {ticket} ===\n")

        current_index = STEP_ORDER.index(current_step) if current_step in STEP_ORDER else -1

        if current_index < 0:
            print(f"   ❌ Cannot continue from step: {current_step}")
            return 1

        if current_index >= len(STEP_ORDER) - 1:
            print(f"   ⚠️  Already at final step: {current_step}")
            return 1

        next_step = STEP_ORDER[current_index + 1]

        handoff_reasons = self._handoff_blockers(ticket, entry)
        dor_reasons = self._dor_blockers(entry) if next_step == "develop" else []
        reasons = dor_reasons + handoff_reasons

        if next_step == "develop":
            if dor_reasons or (handoff_reasons and not force):
                result = "refused"
            elif handoff_reasons:
                result = "forced"
            else:
                result = "passed"
            self._record_history(ticket, "dor_gate", {
                "from": current_step,
                "to": next_step,
                "result": result,
                "missing": self._dor_missing(entry),
                "reasons": reasons,
            })

        if dor_reasons or (handoff_reasons and not force):
            print(f"   ❌ Cannot continue from {current_step} to {next_step}:")
            for reason in reasons:
                print(f"   - {reason}")
            if dor_reasons:
                print(f"   ⚠️  --force does not override the DoR gate. Record pass or a waiver:")
                print(f"   python .opencode/scripts/pipeline.py dor {ticket} --json '...'")
                print(f"   python .opencode/scripts/pipeline.py waive {ticket} <DOR_ID> --reason ... --by ...")
            else:
                print(f"   ⚠️  Complete the step with a COMPLETED handoff before continuing")
                print(f"   Use 'what-missed' to see what was lost in this step")
            return 1

        print(f"Advancing from {current_step} to {next_step}")

        if handoff_reasons:
            self._record_history(ticket, "forced_advance", {
                "from": current_step,
                "to": next_step,
                "bypassed": handoff_reasons,
                "cleared_block": bool(entry.get("blocked")),
            })

        entry["current_step"] = next_step
        entry["status"] = "in_progress"
        entry["blocked"] = False
        entry["step_reported_complete"] = False
        entry.pop("interrupted", None)
        entry.pop("interrupted_reason", None)
        entry["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        self._record_history(ticket, "step_advance", {
            "from": current_step,
            "to": next_step,
            "state": entry
        })

        print(f"   ✓ Pipeline advanced to: {next_step}")
        return 0

    def dry_run(
        self, ticket: str, action: str, params: Optional[Dict] = None,
        now: Optional[datetime] = None,
    ) -> None:
        """Preview pipeline action without executing."""
        print(f"=== Dry Run: {ticket} - {action} ===\n")
        
        entry = self._peek_entry(ticket)
        print(f"Current state:")
        print(f"  Step: {entry.get('current_step')}")
        print(f"  Cycles: {entry.get('cycle_counts')}")
        print(f"  Status: {entry.get('status')}")
        
        # Simulate action
        if action == "show_state":
            print(f"\nWould show pipeline state")
        elif action == "resume":
            interruption = self._detect_interruption(ticket, now)
            if interruption and interruption.get("interrupted"):
                print(f"\nWould resume at step: {entry.get('current_step')}")
                print(f"  ⚠️  What was missed:")
                missed = interruption['what_was_missed']
                print(f"    - {missed['step']}: {missed['current_cycles']}/{missed['expected_cycles']} cycles")
            else:
                print(f"\nWould resume at step: {entry.get('current_step')}")
        elif action == "what_missed":
            interruption = self._detect_interruption(ticket, now)
            if interruption and interruption.get("interrupted"):
                print(f"\nWould show what was missed:")
                missed = interruption['what_was_missed']
                print(f"  - Step: {missed['step']}")
                print(f"  - Expected: {missed['expected_cycles']} cycles")
                print(f"  - Current: {missed['current_cycles']} cycles")
        elif action == "continue":
            step_order = ["plan", "develop", "complete"]
            current_step = entry.get("current_step")
            if current_step in step_order:
                current_index = step_order.index(current_step)
                if current_index < len(step_order) - 1:
                    next_step = step_order[current_index + 1]
                    print(f"\nWould advance from {current_step} to {next_step}")
        
        print(f"\n✅ Dry run completed - no changes made")

    def check_stuck(self, ticket: str, now: Optional[datetime] = None) -> None:
        """Detect and alert on stuck pipelines. Uses the same rule as show and resume."""
        print(f"=== Checking for Stuck Pipelines: {ticket} ===\n")

        now = now or _utc_now()
        interruption = self._detect_interruption(ticket, now)
        if interruption and interruption.get("interrupted"):
            print(f"⚠️  STUCK PIPELINE DETECTED!")
            print(f"   Reason: {interruption['reason']}")
            print(f"   Step: {interruption['interrupted_step']}")
            print(f"   Interrupted at: {interruption['interrupted_at']}")

            # Calculate how long it's been stuck
            interrupted_time = _parse_timestamp(interruption['interrupted_at'])
            if interrupted_time is None:
                print(f"   ❌ Could not calculate stuck duration")
            else:
                hours_stuck = (now - interrupted_time).total_seconds() / 3600
                print(f"   Stuck for: {hours_stuck:.1f} hours")

                if hours_stuck > 24:
                    print(f"   🚨 CRITICAL: Pipeline has been stuck for over 24 hours!")
                elif hours_stuck > 12:
                    print(f"   ⚠️  WARNING: Pipeline has been stuck for over 12 hours!")
                elif hours_stuck > 1:
                    print(f"   ⚠️  WARNING: Pipeline has been stuck for over 1 hour!")

            print(f"\n   What was missed:")
            missed = interruption['what_was_missed']
            print(f"   - Step: {missed['step']}")
            print(f"   - Expected work: {missed['expected_work']}")
            print(f"   - Status: {missed['work_status']}")

            print(f"\n   🔄 Suggested actions:")
            print(f"   - 'resume' to attempt to complete the stuck step")
            if interruption['reason'].startswith("blocked"):
                print(f"   - 'resume --force' after the Product Owner resolves the blocker")
            print(f"   - 'reset' to clear all progress and start over")
            print(f"   - 'escalate' to get help from the Product Owner")
        else:
            print(f"✅ No stuck pipelines detected")

    def reset(self, ticket: str, force: bool = False) -> None:
        """Reset pipeline to initial state."""
        if not force:
            entry = self._peek_entry(ticket)
            print(f"⚠️  WARNING: This will delete all pipeline progress for {ticket}")
            print(f"   Current state:")
            print(f"   - Step: {entry.get('current_step')}")
            print(f"   - Cycles: {entry.get('cycle_counts')}")
            print(f"   - Status: {entry.get('status')}")
            print(f"\n   Use --force to confirm reset")
            return
        
        entry = self._get_entry(ticket)
        print(f"=== Resetting Pipeline: {ticket} ===\n")
        
        # Reset to initial state
        self.state[ticket] = self._default_entry()
        
        self._record_history(ticket, "pipeline_reset", self.state[ticket])
        self._save_state()
        
        print(f"   ✓ Pipeline reset to initial state")
        print(f"   - Step: plan")
        print(f"   - Status: not_started")

    def get_history(self, ticket: str) -> None:
        """Show pipeline history."""
        if ticket not in self.history:
            print(f"No history found for {ticket}")
            return
        
        print(f"=== Pipeline History: {ticket} ===\n")
        print(f"Created: {self.history[ticket].get('created', 'N/A')}")
        print(f"Last Updated: {self.history[ticket].get('last_updated', 'N/A')}")
        
        if not self.history[ticket].get("actions"):
            print(f"No actions recorded")
            return
        
        print(f"\nAction History:")
        for i, action in enumerate(self.history[ticket]["actions"][-10:], 1):
            print(f"  {i}. {action['timestamp'][:19]} - {action['action']}")

    def set_mode(self, ticket: str, mode: str) -> None:
        """Set development mode for a ticket."""
        entry = self._get_entry(ticket)
        
        if mode not in ["interactive", "automated"]:
            print(f"❌ Invalid mode: {mode}. Must be 'interactive' or 'automated'")
            return
        
        entry["development_mode"] = mode
        entry["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        
        print(f"✓ Development mode set to: {mode} for {ticket}")

    def get_mode(self, ticket: str) -> None:
        """Get persisted mode for a ticket."""
        entry = self._peek_entry(ticket)
        mode = entry.get("development_mode", "interactive")
        print(f"Mode for {ticket}: {mode}")

    def record_handoff(
        self,
        ticket: str,
        from_agent: str,
        to_agent: str,
        step: str,
        status: str,
        artifacts: Optional[List[str]] = None,
        accomplishments: Optional[List[str]] = None,
        issues: Optional[List[str]] = None,
        next_steps: Optional[List[str]] = None,
        mode: Optional[str] = None,
        cycle: Optional[int] = None,
        max_cycles: int = 3,
    ) -> Dict[str, Any]:
        """Record a handoff in pipeline history and return its JIRA comment body.

        The ticket may be any work item reference (JIRA, GitHub, or generic). The
        script has no tracker client. The caller posts the returned markdown
        through the Atlassian MCP (atlassian_addCommentToJiraIssue).
        """
        missing = [name for name, value in (("from", from_agent), ("to", to_agent), ("status", status)) if not value]
        if missing:
            raise ValueError(f"handoff requires non-empty fields: {', '.join(missing)}")
        status = str(status).strip().upper()
        if status not in HANDOFF_STATUSES:
            raise ValueError(
                f"handoff status must be one of {', '.join(HANDOFF_STATUSES)}, got {status!r}"
            )
        work_item = parse_work_item_ref(ticket)
        ticket = work_item["key"]

        entry = self._get_entry(ticket)
        handoff = {
            "ticket": ticket,
            "tracker": work_item["tracker"],
            "from": from_agent,
            "to": to_agent,
            "step": step,
            "status": status,
            "artifacts": list(artifacts or []),
            "accomplishments": list(accomplishments or []),
            "issues": list(issues or []),
            "next_steps": list(next_steps or []),
            "mode": mode or entry.get("development_mode", "interactive"),
            "cycle": cycle,
            "max_cycles": max_cycles,
        }
        self._apply_handoff(entry, handoff)
        self._record_history(ticket, "handoff", handoff)
        return handoff

    def _apply_handoff(self, entry: Dict[str, Any], handoff: Dict[str, Any]) -> None:
        """Apply a recorded handoff to the pipeline state (PRO-407, AC-2).

        BLOCKED blocks the pipeline and raises the escalation level. COMPLETED clears
        the block and counts one completed cycle for the current step. IN_PROGRESS
        marks the step in progress, but it does not clear a block: a blocked pipeline
        stays blocked until a COMPLETED handoff or a forced continue or resume.
        """
        status = str(handoff["status"]).upper()
        step = entry.get("current_step")
        if status == "BLOCKED":
            entry["blocked"] = True
            entry["status"] = "blocked"
            entry["escalation_level"] = int(entry.get("escalation_level", 0)) + 1
        elif status == "COMPLETED":
            entry["blocked"] = False
            if entry.get("status") == "blocked":
                entry["status"] = "in_progress"
            entry["step_reported_complete"] = True
            cycle_counts = entry.setdefault("cycle_counts", {})
            cycle_counts[step] = cycle_counts.get(step, 0) + 1
        elif status == "IN_PROGRESS":
            entry["step_reported_complete"] = False
            if not entry.get("blocked"):
                entry["status"] = "in_progress"
        entry["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_state()

    @staticmethod
    def render_handoff_comment(handoff: Dict[str, Any]) -> str:
        """Render a handoff as the standard JIRA comment (PRO-407 template)."""

        def bullets(items: List[str], empty: str) -> List[str]:
            return [f"* {item}" for item in items] if items else [empty]

        cycle_part = (
            f"Cycle: {handoff['cycle']}/{handoff['max_cycles']}"
            if handoff.get("cycle") is not None
            else "Cycle: n/a"
        )
        lines = [
            f"Handoff: {handoff['from']} → {handoff['to']} (Step: {handoff.get('step') or 'n/a'})",
            "",
            "Artifacts:",
            *bullets(handoff["artifacts"], "* None"),
            "",
            f"Status: {handoff['status']}",
            "",
            "Accomplishments:",
            *bullets(handoff["accomplishments"], "* None"),
            "",
            "Issues / Blockers:",
            *bullets(handoff["issues"], "* None"),
            "",
            "Next Steps:",
            *bullets(handoff["next_steps"], "* None"),
            "",
            f"Metadata: Mode: {handoff['mode']} | {cycle_part}",
            f"Work item: {handoff.get('ticket', 'n/a')} "
            f"(tracker: {handoff.get('tracker', 'jira')})",
        ]
        return "\n".join(lines)


def main():
    """Main entry point for pipeline management tool."""
    # Parse raw args to handle space-separated commands like "show state"
    raw_args = sys.argv[1:]

    # Build a clean args list that argparse can handle
    clean_args = []
    i = 0
    while i < len(raw_args):
        arg = raw_args[i]
        if arg == "show" and i + 1 < len(raw_args) and raw_args[i + 1] == "state":
            # "show state" -> "showstate"
            clean_args.append("showstate")
            i += 2
        else:
            clean_args.append(arg)
            i += 1

    parser = argparse.ArgumentParser(description="Enhanced pipeline management tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # State management
    showstate_parser = subparsers.add_parser("showstate", help="Show current pipeline state")
    showstate_parser.add_argument("ticket", help="JIRA ticket key")
    showstate_parser.set_defaults(func=lambda args: manager.show_state(args.ticket))

    reset_parser = subparsers.add_parser("reset", help="Reset pipeline to initial state")
    reset_parser.add_argument("ticket", help="JIRA ticket key")
    reset_parser.add_argument("--force", action="store_true", help="Confirm reset")
    reset_parser.set_defaults(func=lambda args: manager.reset(args.ticket, args.force))

    history_parser = subparsers.add_parser("history", help="Show pipeline history")
    history_parser.add_argument("ticket", help="JIRA ticket key")
    history_parser.set_defaults(func=lambda args: manager.get_history(args.ticket))

    # Enhanced workflow commands
    resume_parser = subparsers.add_parser("resume", help="Resume pipeline at current step")
    resume_parser.add_argument("ticket", help="JIRA ticket key")
    resume_parser.add_argument("--force", action="store_true", help="Force resume without validation")
    resume_parser.set_defaults(func=lambda args: manager.resume(args.ticket, args.force))

    interrupt_parser = subparsers.add_parser(
        "interrupt", help="Mark a pipeline interrupted until it is resumed"
    )
    interrupt_parser.add_argument("ticket", help="JIRA ticket key")
    interrupt_parser.add_argument("--reason", default="", help="Why the pipeline is interrupted")
    interrupt_parser.set_defaults(func=lambda args: manager.interrupt(args.ticket, args.reason))

    continue_parser = subparsers.add_parser("continue", help="Advance to next pipeline step")
    continue_parser.add_argument("ticket", help="JIRA ticket key")
    continue_parser.add_argument("--force", action="store_true", help="Force advance without validation")
    continue_parser.set_defaults(func=lambda args: manager.continue_step(args.ticket, args.force))

    proceed_parser = subparsers.add_parser("proceed", help="Proceed with current step execution")
    proceed_parser.add_argument("ticket", help="JIRA ticket key")
    proceed_parser.add_argument("--force", action="store_true", help="Force proceed without validation")
    proceed_parser.set_defaults(func=lambda args: manager.resume(args.ticket, args.force))

    what_missed_parser = subparsers.add_parser("what-missed", help="Show what work was missed")
    what_missed_parser.add_argument("ticket", help="JIRA ticket key")
    what_missed_parser.set_defaults(func=lambda args: manager.what_missed(args.ticket))

    dry_run_parser = subparsers.add_parser("dry-run", help="Preview action without executing")
    dry_run_parser.add_argument("ticket", help="JIRA ticket key")
    dry_run_parser.add_argument("action", help="Action to preview (resume, continue, proceed)")
    dry_run_parser.set_defaults(func=lambda args: manager.dry_run(args.ticket, args.action))

    check_stuck_parser = subparsers.add_parser("check-stuck", help="Detect stuck pipelines")
    check_stuck_parser.add_argument("ticket", help="JIRA ticket key")
    check_stuck_parser.set_defaults(func=lambda args: manager.check_stuck(args.ticket))

    set_mode_parser = subparsers.add_parser("set-mode", help="Set development mode")
    set_mode_parser.add_argument("ticket", help="JIRA ticket key")
    set_mode_parser.add_argument("mode", help="Mode: 'interactive' or 'automated'")
    set_mode_parser.set_defaults(func=lambda args: manager.set_mode(args.ticket, args.mode))

    get_mode_parser = subparsers.add_parser("get-mode", help="Get persisted mode")
    get_mode_parser.add_argument("ticket", help="JIRA ticket key")
    get_mode_parser.set_defaults(func=lambda args: manager.get_mode(args.ticket))

    dor_parser = subparsers.add_parser(
        "dor", help="Record or show the Definition of Ready checklist"
    )
    dor_parser.add_argument("ticket", help="JIRA ticket key")
    dor_parser.add_argument("--json", dest="json_values", default=None,
                            help='Checklist as JSON, e.g. \'{"D1": "pass", "D2": "fail"}\'')

    def run_dor(args) -> None:
        if args.json_values is None:
            manager.show_dor(args.ticket)
        else:
            manager.record_dor(args.ticket, json.loads(args.json_values))
            print(f"✓ DoR checklist recorded for {args.ticket}")

    dor_parser.set_defaults(func=run_dor)

    waive_parser = subparsers.add_parser("waive", help="Waive one Definition of Ready item")
    waive_parser.add_argument("ticket", help="JIRA ticket key")
    waive_parser.add_argument("dor_id", help="DoR item to waive (D1-D7)")
    waive_parser.add_argument("--reason", required=True, help="Why the item is waived")
    waive_parser.add_argument("--by", required=True, help="Who waives it (for example PO)")
    waive_parser.set_defaults(
        func=lambda args: manager.waive(args.ticket, args.dor_id, args.reason, args.by)
    )

    handoff_parser = subparsers.add_parser("handoff", help="Record an agent handoff and print its JIRA comment")
    handoff_parser.add_argument(
        "ticket",
        help="Work item reference: JIRA key (PRO-123), GitHub (GH-456, owner/repo#456), "
        "or generic id",
    )
    handoff_parser.add_argument("--from", dest="from_agent", required=True, help="Sending agent")
    handoff_parser.add_argument("--to", dest="to_agent", required=True, help="Receiving agent")
    handoff_parser.add_argument("--step", default="", help="Pipeline step name")
    handoff_parser.add_argument("--status", required=True, help="Work status, e.g. COMPLETED or BLOCKED")
    handoff_parser.add_argument("--artifact", action="append", default=[], help="Artifact path (repeatable)")
    handoff_parser.add_argument("--accomplishment", action="append", default=[], help="Accomplishment (repeatable)")
    handoff_parser.add_argument("--issue", action="append", default=[], help="Issue or blocker (repeatable)")
    handoff_parser.add_argument("--next-step", dest="next_steps", action="append", default=[], help="Next step (repeatable)")
    handoff_parser.add_argument("--mode", default=None, help="Override mode (default: persisted mode)")
    handoff_parser.add_argument("--cycle", type=int, default=None, help="Current cycle number")
    handoff_parser.add_argument("--max-cycles", type=int, default=3, help="Maximum cycles")
    handoff_parser.set_defaults(
        func=lambda args: print(
            PipelineManager.render_handoff_comment(
                manager.record_handoff(
                    args.ticket,
                    args.from_agent,
                    args.to_agent,
                    args.step,
                    args.status,
                    artifacts=args.artifact,
                    accomplishments=args.accomplishment,
                    issues=args.issue,
                    next_steps=args.next_steps,
                    mode=args.mode,
                    cycle=args.cycle,
                    max_cycles=args.max_cycles,
                )
            )
        )
    )

    reconcile_parser = subparsers.add_parser(
        "reconcile", help="Check that changed areas have their living documents updated"
    )
    reconcile_parser.add_argument("ticket", help="JIRA ticket key")
    reconcile_parser.add_argument("--base", default="master", help="Base ref (default: master)")
    reconcile_parser.add_argument(
        "--changed", action="append", default=None,
        help="Changed path (repeatable). Skips the git diff when given.",
    )
    reconcile_parser.set_defaults(
        func=lambda args: manager.reconcile(args.ticket, args.base, args.changed)
    )

    # Parse and execute
    args = parser.parse_args(clean_args)
    if not hasattr(args, 'func'):
        parser.print_help()
        return

    # Loaded after parsing so --help works, and before any command so that a corrupt
    # state or history file is reported (exit 1) by every command, read or write.
    try:
        manager = PipelineManager()
    except StateFileError as exc:
        print(f"❌ {exc}")
        sys.exit(1)

    try:
        exit_code = args.func(args)
        if isinstance(exit_code, int) and exit_code:
            sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

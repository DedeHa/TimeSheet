#!/usr/bin/env python3
"""Enhanced pipeline management tool for TimeSheetAlgo agent team.

This tool provides commands to:
- Initialize pipeline state for new feature requests (init)
- Resume/continue/proceed pipeline steps that are stuck
- Show what work was missed in interrupted pipelines
- Preview pipeline actions (dry-run)
- Detect and alert on stuck pipelines
- Manage pipeline history and transitions

Usage:
    python pipeline.py <command> <ticket> [options]

Commands:
    init <ticket>                 Initialize pipeline state for new feature
    show state <ticket>           Show current pipeline state
    resume <ticket>               Resume pipeline at current step
    continue <ticket>             Continue to next pipeline step
    proceed <ticket>              Proceed with current step execution
    what-missed <ticket>          Show what work was missed in interrupted pipeline
    dry-run <ticket> <command>    Preview action without executing
    check-stuck <ticket>          Detect and alert on stuck pipelines
    reset <ticket>                Reset all cycles and state
    history <ticket>              Show pipeline history
    set-mode <ticket> <mode>      Set interactive/automated mode
    get-mode <ticket>             Show persisted mode
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import fcntl
except ImportError:
    fcntl = None

STATE_PATH = Path(__file__).resolve().parent.parent / "pipeline-state.json"
HISTORY_PATH = Path(__file__).resolve().parent.parent / "pipeline-history.json"

LOCK_TIMEOUT = 5.0
PIPELINE_STEPS = ("plan", "develop", "complete")
CANONICAL_STATES = {
    "backlog": "Ticket is created and awaiting readiness checks.",
    "plan": "Requirements and implementation plan are being prepared.",
    "develop": "Implementation is in progress.",
    "complete": "Validation and closure work is underway.",
    "approved": "Implementation has passed validation and is ready for closure.",
    "released": "The feature has been released and closed out.",
}
STATE_TRANSITIONS = {
    "backlog": ("plan",),
    "plan": ("develop", "blocked"),
    "develop": ("complete", "blocked"),
    "complete": ("approved", "blocked"),
    "approved": ("released",),
    "released": (),
    "blocked": ("plan", "develop", "complete"),
}


def _acquire_lock(fd):
    """Acquire an exclusive file lock, non-blocking with retry."""
    if fcntl is None:
        return
    import time

    deadline = time.time() + LOCK_TIMEOUT
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.time() >= deadline:
                return
            time.sleep(0.05)


def _release_lock(fd):
    """Release an exclusive file lock."""
    if fcntl is None:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


def _ensure_migrated() -> None:
    """Run migration if new state missing but old state exists."""
    if STATE_PATH.exists():
        return
    try:
        from migrate_pipeline_state import migrate_pipeline_state

        migrate_pipeline_state()
    except Exception:
        pass


class PipelineManager:
    """Enhanced pipeline management with resume/continue/proceed functionality."""

    def __init__(self):
        """Initialize the pipeline manager with state and history."""
        self.state = self._load_state()
        self.history = self._load_history()

    def _load_state(self) -> Dict[str, Any]:
        """Load the pipeline state file, triggering migration if needed."""
        _ensure_migrated()
        if not STATE_PATH.exists():
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            return {}
        try:
            with STATE_PATH.open("r+", encoding="utf-8") as fh:
                _acquire_lock(fh)
                try:
                    data = json.load(fh)
                finally:
                    _release_lock(fh)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_state(self) -> None:
        """Persist the pipeline state file atomically with locking."""
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.state, fh, indent=2, sort_keys=True)
        try:
            with STATE_PATH.open("r+", encoding="utf-8") as fh:
                _acquire_lock(fh)
                try:
                    tmp.replace(STATE_PATH)
                finally:
                    _release_lock(fh)
        except OSError:
            tmp.replace(STATE_PATH)

    def _load_history(self) -> Dict[str, Any]:
        """Load the pipeline history file."""
        if not HISTORY_PATH.exists():
            HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            return {}
        try:
            with HISTORY_PATH.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_history(self) -> None:
        """Persist the pipeline history file atomically."""
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = HISTORY_PATH.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.history, fh, indent=2, sort_keys=True)
        tmp.replace(HISTORY_PATH)

    def _canonical_state(self, entry: Dict[str, Any]) -> str:
        """Resolve the canonical workflow state for an entry."""
        workflow_state = entry.get("workflow_state")
        if workflow_state in CANONICAL_STATES:
            return workflow_state
        current_step = entry.get("current_step")
        if current_step in PIPELINE_STEPS:
            return current_step
        return "backlog"

    def _normalize_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure the workflow entry includes the canonical state fields."""
        entry.setdefault("development_mode", "interactive")
        entry.setdefault("current_step", "plan")
        entry.setdefault("workflow_state", "backlog")
        entry.setdefault("cycle_counts", {"plan": 0, "develop": 0, "complete": 0})
        entry.setdefault("last_updated", datetime.now(timezone.utc).isoformat())
        entry.setdefault("status", "not_started")
        entry.setdefault("blocked", False)
        entry.setdefault("escalation_level", 0)
        entry.setdefault("interrupted", False)
        entry.setdefault("interrupted_step", None)
        entry.setdefault("interrupted_at", None)
        entry.setdefault("story_points", None)
        entry.setdefault("blockers", [])
        entry.setdefault("last_action", "pipeline_initialized")
        entry.setdefault("required_next_step", "plan")
        entry["workflow_state"] = self._canonical_state(entry)
        return entry

    def _validate_transition(self, ticket: str, next_step: str) -> tuple[bool, str]:
        """Validate a transition against the canonical workflow state machine."""
        entry = self._get_entry(ticket)
        if entry is None:
            return False, f"Ticket '{ticket}' has no pipeline state entry. Initialize it first."

        current_step = entry.get("current_step")
        current_state = self._canonical_state(entry)

        if next_step not in STATE_TRANSITIONS.get(current_state, ()):
            return (
                False,
                (
                    f"Invalid transition from '{current_state}' "
                    f"to '{next_step}'. Allowed states: "
                    f"{', '.join(STATE_TRANSITIONS.get(current_state, ())) or 'none'}"
                ),
            )

        if current_step in PIPELINE_STEPS and entry.get("cycle_counts", {}).get(current_step, 0) == 0 and current_state != "blocked":
            return (
                False,
                f"Cannot advance from '{current_step}' because the current step has not been completed yet.",
            )

        if entry.get("blocked") and next_step not in STATE_TRANSITIONS.get("blocked", ()):
            return (
                False,
                "The ticket is blocked and must be resolved before continuing the pipeline.",
            )

        return True, ""

    def _record_transition(self, ticket: str, from_step: str, to_step: str) -> None:
        """Persist a state transition to history."""
        entry = self._get_entry(ticket)
        if entry is None:
            return
        history = self.history.setdefault(ticket, {"created": entry.get("last_updated"), "actions": [], "transitions": []})
        transition = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from": from_step,
            "to": to_step,
        }
        history.setdefault("transitions", []).append(transition)
        self._save_history()

    def _get_entry(self, ticket: str) -> Dict[str, Any] | None:
        """Get pipeline entry for a ticket, or None if it doesn't exist."""
        if ticket not in self.state:
            return None
        return self._normalize_entry(self.state[ticket])

    def _ensure_entry(self, ticket: str) -> Dict[str, Any]:
        """Get or create a pipeline entry for a ticket."""
        if ticket not in self.state:
            self.state[ticket] = {
                "development_mode": "interactive",
                "current_step": "plan",
                "workflow_state": "backlog",
                "cycle_counts": {"plan": 0, "develop": 0, "complete": 0},
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "status": "not_started",
                "blocked": False,
                "escalation_level": 0,
                "interrupted": False,
                "interrupted_step": None,
                "interrupted_at": None,
                "story_points": None,
                "blockers": [],
                "last_action": "pipeline_created",
                "required_next_step": "plan",
            }
            self._save_state()
            self._record_history(ticket, "pipeline_created", self.state[ticket])
        self.state[ticket] = self._normalize_entry(self.state[ticket])
        return self.state[ticket]

    def _record_history(
        self, ticket: str, action: str, details: Dict[str, Any]
    ) -> None:
        """Record pipeline state change in history."""
        timestamp = datetime.now(timezone.utc).isoformat()
        if ticket not in self.history:
            self.history[ticket] = {
                "created": timestamp,
                "actions": [],
                "transitions": [],
            }
        self.history[ticket]["actions"].append(
            {"timestamp": timestamp, "action": action, "details": details}
        )
        self.history[ticket]["last_updated"] = timestamp
        self._save_history()

    def _detect_interruption(self, ticket: str) -> Optional[Dict[str, Any]]:
        """Detect if a pipeline was interrupted and what was missed."""
        entry = self._get_entry(ticket)
        if entry is None:
            return None

        # Check if pipeline is stuck in a step
        current_step = entry.get("current_step")
        cycle_count = entry.get("cycle_counts", {}).get(current_step, 0)

        # If the current step has zero cycles but is in progress, it's an
        # interruption (the step was started but never completed).
        if cycle_count == 0 and entry.get("status") == "in_progress":
            return {
                "interrupted": True,
                "interrupted_step": current_step,
                "interrupted_at": entry.get("last_updated"),
                "what_was_missed": self._get_missed_work(ticket, entry),
            }

        return None

    def _get_missed_work(self, ticket: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Determine what work was missed in an interrupted pipeline."""
        current_step = entry.get("current_step")
        cycle_counts = entry.get("cycle_counts", {})

        # Map steps to expected work
        step_expectations = {
            "plan": {
                "expected_cycles": 1,
                "expected_work": (
                    "Architecture plan with implementation plan (Part A/B/C)"
                ),
                "current_cycles": cycle_counts.get("plan", 0),
            },
            "develop": {
                "expected_cycles": 1,
                "expected_work": "Implementation with rollout steps completed",
                "current_cycles": cycle_counts.get("develop", 0),
            },
            "complete": {
                "expected_cycles": 1,
                "expected_work": "Testing with validation and JIRA closure",
                "current_cycles": cycle_counts.get("complete", 0),
            },
        }

        expectation = step_expectations.get(current_step, {})

        return {
            "step": current_step,
            "expected_cycles": expectation.get("expected_cycles", 1),
            "current_cycles": expectation.get("current_cycles", 0),
            "expected_work": expectation.get("expected_work", "Unknown work"),
            "work_status": (
                "INCOMPLETE"
                if expectation.get("current_cycles", 0) == 0
                else "COMPLETE"
            ),
        }

    def generate_handoff_payload(self, ticket: str) -> Dict[str, Any]:
        """Build a standard handoff payload for downstream agent dispatch."""
        entry = self._get_entry(ticket)
        interruption = self._detect_interruption(ticket)
        if entry is None:
            return {
                "ticket": ticket,
                "current_step": "plan",
                "workflow_state": "backlog",
                "status": "not_started",
                "development_mode": "interactive",
                "story_points": None,
                "blocked": False,
                "blockers": [],
                "cycle_counts": {"plan": 0, "develop": 0, "complete": 0},
                "last_action": "unknown",
                "required_next_step": "plan",
                "interrupted": False,
                "interruption": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "ticket": ticket,
            "current_step": entry.get("current_step", "plan"),
            "workflow_state": entry.get("workflow_state", self._canonical_state(entry)),
            "status": entry.get("status", "not_started"),
            "development_mode": entry.get("development_mode", "interactive"),
            "story_points": entry.get("story_points"),
            "blocked": entry.get("blocked", False),
            "blockers": entry.get("blockers", []),
            "cycle_counts": entry.get("cycle_counts", {"plan": 0, "develop": 0, "complete": 0}),
            "last_action": entry.get("last_action", "unknown"),
            "required_next_step": entry.get("required_next_step", "plan"),
            "interrupted": bool(interruption and interruption.get("interrupted")),
            "interruption": interruption,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def recover_ticket(self, ticket: str) -> Dict[str, Any]:
        """Return the canonical recovery recommendation for a ticket."""
        entry = self._get_entry(ticket)
        interruption = self._detect_interruption(ticket)
        payload = self.generate_handoff_payload(ticket)
        if entry is None:
            payload["recovery"] = {
                "is_interrupted": False,
                "missed_work": None,
                "suggested_action": "init",
                "should_escalate": False,
            }
            return payload
        payload["recovery"] = {
            "is_interrupted": bool(interruption and interruption.get("interrupted")),
            "missed_work": interruption.get("what_was_missed") if interruption else None,
            "suggested_action": (
                "resume"
                if interruption and interruption.get("interrupted")
                else "continue"
                if entry.get("current_step") in PIPELINE_STEPS
                else "plan"
            ),
            "should_escalate": entry.get("blocked", False)
            or (entry.get("status") == "blocked")
            or entry.get("escalation_level", 0) > 0,
        }
        return payload

    def show_state(self, ticket: str) -> None:
        """Show current pipeline state with interruption detection."""
        entry = self._get_entry(ticket)
        if entry is None:
            print(f"No pipeline state found for {ticket}.")
            print("Use 'init' command to create the entry first.")
            return

        print(f"=== Pipeline State: {ticket} ===\n")

        print(f"Current Step: {entry.get('current_step', 'N/A')}")
        print(f"Workflow State: {entry.get('workflow_state', self._canonical_state(entry))}")
        print(f"Status: {entry.get('status', 'N/A')}")
        print(f"Development Mode: {entry.get('development_mode', 'interactive')}")
        print(f"Last Updated: {entry.get('last_updated', 'N/A')}")

        cycle_counts = entry.get("cycle_counts", {})
        print("\nCycle Counts:")
        print(f"  Plan: {cycle_counts.get('plan', 0)} (max: 3)")
        print(f"  Develop: {cycle_counts.get('develop', 0)} (max: 3)")
        print(f"  Complete: {cycle_counts.get('complete', 0)} (max: 3)")

        # Check for interruption
        interruption = self._detect_interruption(ticket)
        if interruption and interruption.get("interrupted"):
            print("\n⚠️  INTERRUPTED PIPELINE DETECTED!")
            print(f"   Step: {interruption['interrupted_step']}")
            print(f"   Interrupted at: {interruption['interrupted_at']}")
            print("\n   What was missed:")
            missed = interruption["what_was_missed"]
            print(f"   - Step: {missed['step']}")
            print(f"   - Expected cycles: {missed['expected_cycles']}")
            print(f"   - Current cycles: {missed['current_cycles']}")
            print(f"   - Expected work: {missed['expected_work']}")
            print(f"   - Status: {missed['work_status']}")
        else:
            print("\n✅ Pipeline is not interrupted")

        print(f"\nEscalation Level: {entry.get('escalation_level', 0)}")
        print(f"Blocked: {entry.get('blocked', False)}")

    def resume(self, ticket: str, force: bool = False) -> None:
        """Resume pipeline at the current step with validation."""
        entry = self._ensure_entry(ticket)
        current_step = entry.get("current_step")

        print(f"=== Resuming Pipeline: {ticket} ===\n")

        # Check for interruption
        interruption = self._detect_interruption(ticket)
        if interruption and interruption.get("interrupted"):
            print(
                f"⚠️  Pipeline was interrupted at step: "
                f"{interruption['interrupted_step']}"
            )
            print("   What was missed:")
            missed = interruption["what_was_missed"]
            print(f"   - {missed['step']}: {missed['expected_work']}")
            print(
                f"   - Cycles: {missed['current_cycles']}/{missed['expected_cycles']}"
            )

            if not force:
                print(
                    "\n   ⚠️  Pipeline needs to be reset or completed before resuming."
                )
                print("   Use 'reset' to clear all progress and start over.")
                print("   Or provide --force to skip validation.")
                return

        entry["status"] = "in_progress"
        entry["workflow_state"] = self._canonical_state(entry)
        entry["last_action"] = "pipeline_resumed"
        entry["required_next_step"] = current_step

        print(f"Resuming pipeline at step: {current_step}")

        # Clear interruption flag if present
        if entry.get("interrupted"):
            entry["interrupted"] = False
            entry["interrupted_step"] = None
            entry["interrupted_at"] = None
            entry["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._save_state()
            self._record_history(ticket, "interruption_cleared", entry)
            print("   ✓ Interruption flag cleared")

        self._save_state()
        self._record_history(ticket, "pipeline_resumed", entry)
        print("\n✅ Pipeline resumed successfully")

    def what_missed(self, ticket: str) -> None:
        """Show what work was missed in an interrupted pipeline."""
        entry = self._get_entry(ticket)
        if entry is None:
            print(f"No pipeline state found for {ticket}.")
            return

        interruption = self._detect_interruption(ticket)
        if not interruption or not interruption.get("interrupted"):
            print(f"No interrupted pipeline found for {ticket}")
            print("Pipeline status: in_progress, but not interrupted")
            return

        print(f"⚠️  Pipeline interrupted at: {interruption['interrupted_at']}")
        print(f"   Step: {interruption['interrupted_step']}\n")

        missed = interruption["what_was_missed"]
        print("What was missed:")
        print(f"  Step: {missed['step']}")
        print(f"  Expected cycles: {missed['expected_cycles']}")
        print(f"  Current cycles: {missed['current_cycles']}")
        print(f"  Expected work: {missed['expected_work']}")
        print(f"  Status: {missed['work_status']}\n")

        if missed["current_cycles"] == 0:
            print(f"  💡 This means the {missed['step']} step was never executed.")
            print("  🔄 Use 'resume' to attempt to complete this step.")
            print(
                "  ⚠️  If the step truly cannot be completed, use 'reset' to start over."
            )

        print("\nCurrent pipeline state:")
        print(f"  Step: {entry.get('current_step')}")
        print(f"  Cycles: {entry.get('cycle_counts')}")
        print(f"  Status: {entry.get('status')}")

    def continue_step(self, ticket: str, force: bool = False) -> None:
        """Advance pipeline to the next step."""
        entry = self._ensure_entry(ticket)
        current_step = entry.get("current_step")

        print(f"=== Continuing Pipeline: {ticket} ===\n")

        step_order = ["plan", "develop", "complete"]
        current_index = (
            step_order.index(current_step) if current_step in step_order else -1
        )

        if current_index < 0:
            print(f"   ❌ Cannot continue from step: {current_step}")
            return

        if current_index >= len(step_order) - 1:
            print(f"   ⚠️  Already at final step: {current_step}")
            return

        next_step = step_order[current_index + 1]

        if not force:
            valid, reason = self._validate_transition(ticket, next_step)
            if not valid:
                print(f"   ❌ {reason}")
                print("   Use --force to override validation when you intentionally want to continue anyway.")
                return

        print(f"Advancing from {current_step} to {next_step}")

        # Update state
        entry["current_step"] = next_step
        entry["workflow_state"] = next_step
        entry["status"] = "in_progress"
        entry["required_next_step"] = next_step
        entry["last_action"] = "step_advance"
        entry["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        self._record_transition(ticket, current_step, next_step)
        self._record_history(
            ticket,
            "step_advance",
            {"from": current_step, "to": next_step, "state": entry},
        )

        print(f"   ✓ Pipeline advanced to: {next_step}")

    def dry_run(self, ticket: str, action: str, params: Optional[Dict] = None) -> None:
        """Preview pipeline action without executing."""
        print(f"=== Dry Run: {ticket} - {action} ===\n")

        entry = self._get_entry(ticket)
        if entry is None:
            print("No pipeline state found for this ticket.")
            print("Use 'init' command to create the entry first.")
            return

        print("Current state:")
        print(f"  Step: {entry.get('current_step')}")
        print(f"  Cycles: {entry.get('cycle_counts')}")
        print(f"  Status: {entry.get('status')}")

        # Simulate action
        if action == "show_state":
            print("\nWould show pipeline state")
        elif action == "resume":
            interruption = self._detect_interruption(ticket)
            if interruption and interruption.get("interrupted"):
                print(f"\nWould resume at step: {entry.get('current_step')}")
                print("  ⚠️  What was missed:")
                missed = interruption["what_was_missed"]
                print(
                    f"    - {missed['step']}: "
                    f"{missed['current_cycles']}/"
                    f"{missed['expected_cycles']} cycles"
                )
            else:
                print(f"\nWould resume at step: {entry.get('current_step')}")
        elif action == "what_missed":
            interruption = self._detect_interruption(ticket)
            if interruption and interruption.get("interrupted"):
                print("\nWould show what was missed:")
                missed = interruption["what_was_missed"]
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

        print("\n✅ Dry run completed - no changes made")

    def check_stuck(self, ticket: str) -> None:
        """Detect and alert on stuck pipelines."""
        entry = self._get_entry(ticket)
        if entry is None:
            print(f"No pipeline state found for {ticket}.")
            return

        print(f"=== Checking for Stuck Pipelines: {ticket} ===\n")

        # Check if pipeline is stuck in a step
        interruption = self._detect_interruption(ticket)
        if interruption and interruption.get("interrupted"):
            print("⚠️  STUCK PIPELINE DETECTED!")
            print(f"   Step: {interruption['interrupted_step']}")
            print(f"   Interrupted at: {interruption['interrupted_at']}")

            # Calculate how long it's been stuck
            try:
                interrupted_time = datetime.fromisoformat(
                    interruption["interrupted_at"]
                )
                current_time = datetime.now(timezone.utc)
                stuck_duration = current_time - interrupted_time

                hours_stuck = stuck_duration.total_seconds() / 3600
                print(f"   Stuck for: {hours_stuck:.1f} hours")

                if hours_stuck > 24:
                    print("   🚨 CRITICAL: Pipeline has been stuck for over 24 hours!")
                elif hours_stuck > 12:
                    print("   ⚠️  WARNING: Pipeline has been stuck for over 12 hours!")
                elif hours_stuck > 1:
                    print("   ⚠️  WARNING: Pipeline has been stuck for over 1 hour!")
            except Exception:
                print("   ❌ Could not calculate stuck duration")

            print("\n   What was missed:")
            missed = interruption["what_was_missed"]
            print(f"   - Step: {missed['step']}")
            print(f"   - Expected work: {missed['expected_work']}")
            print(f"   - Status: {missed['work_status']}")

            print("\n   🔄 Suggested actions:")
            print("   - 'resume' to attempt to complete the stuck step")
            print("   - 'reset' to clear all progress and start over")
            print("   - 'escalate' to get help from the Product Owner")
        else:
            print("✅ No stuck pipelines detected")

    def reset(self, ticket: str, force: bool = False) -> None:
        """Reset pipeline to initial state."""
        if not force:
            entry = self._get_entry(ticket)
            if entry is None:
                print(f"No pipeline state found for {ticket}.")
                print("Use 'init' command to create the entry first.")
                return
            print(f"⚠️  WARNING: This will delete all pipeline progress for {ticket}")
            print("   Current state:")
            print(f"   - Step: {entry.get('current_step')}")
            print(f"   - Cycles: {entry.get('cycle_counts')}")
            print(f"   - Status: {entry.get('status')}")
            print("\n   Use --force to confirm reset")
            return

        entry = self._ensure_entry(ticket)
        print(f"=== Resetting Pipeline: {ticket} ===\n")

        # Reset to initial state
        self.state[ticket] = {
            "development_mode": "interactive",
            "current_step": "plan",
            "workflow_state": "backlog",
            "cycle_counts": {"plan": 0, "develop": 0, "complete": 0},
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "status": "not_started",
            "blocked": False,
            "escalation_level": 0,
            "interrupted": False,
            "interrupted_step": None,
            "interrupted_at": None,
            "story_points": None,
            "blockers": [],
            "last_action": "pipeline_reset",
            "required_next_step": "plan",
        }

        self._record_history(ticket, "pipeline_reset", self.state[ticket])
        self._save_state()

        print("   ✓ Pipeline reset to initial state")
        print("   - Step: plan")
        print("   - Workflow state: backlog")
        print("   - Status: not_started")

    def get_history(self, ticket: str) -> None:
        """Show pipeline history."""
        if ticket not in self.history:
            print(f"No history found for {ticket}")
            return

        print(f"=== Pipeline History: {ticket} ===\n")
        print(f"Created: {self.history[ticket].get('created', 'N/A')}")
        print(f"Last Updated: {self.history[ticket].get('last_updated', 'N/A')}")

        if not self.history[ticket].get("actions"):
            print("No actions recorded")
            return

        print("\nAction History:")
        for i, action in enumerate(self.history[ticket]["actions"][-10:], 1):
            print(f"  {i}. {action['timestamp'][:19]} - {action['action']}")

    def set_mode(self, ticket: str, mode: str) -> None:
        """Set development mode for a ticket."""
        entry = self._ensure_entry(ticket)

        if mode not in ["interactive", "automated"]:
            print(f"❌ Invalid mode: {mode}. Must be 'interactive' or 'automated")
            return

        entry["development_mode"] = mode
        entry["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_state()

        print(f"✓ Development mode set to: {mode} for {ticket}")

    def get_mode(self, ticket: str) -> None:
        """Get persisted mode for a ticket."""
        entry = self._get_entry(ticket)
        if entry is None:
            print(f"Mode for {ticket}: interactive (no state entry found)")
            return
        mode = entry.get("development_mode", "interactive")
        print(f"Mode for {ticket}: {mode}")

    def init(self, ticket: str) -> None:
        """Initialize pipeline state for a new feature request."""
        entry = self._ensure_entry(ticket)
        print(f"✓ Pipeline initialized for {ticket}")
        print(f"  Step: {entry['current_step']}")
        print(f"  Workflow state: {entry['workflow_state']}")
        print(f"  Mode: {entry['development_mode']}")
        print(f"  Status: {entry['status']}")

    def recover_ticket_cli(self, ticket: str) -> None:
        """Print the canonical recovery recommendation for a ticket."""
        payload = self.recover_ticket(ticket)
        print(json.dumps(payload, indent=2, sort_keys=True))


def main():
    """Entry point for the pipeline management tool."""
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

    # Initialize manager first so lambdas can reference it
    manager = PipelineManager()

    parser = argparse.ArgumentParser(description="Enhanced pipeline management tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # State management
    init_parser = subparsers.add_parser("init", help="Initialize pipeline state for a new feature request")
    init_parser.add_argument("ticket", help="JIRA ticket key")
    init_parser.set_defaults(func=lambda args: manager.init(args.ticket))

    showstate_parser = subparsers.add_parser(
        "showstate", help="Show current pipeline state"
    )
    showstate_parser.add_argument("ticket", help="JIRA ticket key")
    showstate_parser.set_defaults(func=lambda args: manager.show_state(args.ticket))

    reset_parser = subparsers.add_parser(
        "reset", help="Reset pipeline to initial state"
    )
    reset_parser.add_argument("ticket", help="JIRA ticket key")
    reset_parser.add_argument("--force", action="store_true", help="Confirm reset")
    reset_parser.set_defaults(func=lambda args: manager.reset(args.ticket, args.force))

    history_parser = subparsers.add_parser("history", help="Show pipeline history")
    history_parser.add_argument("ticket", help="JIRA ticket key")
    history_parser.set_defaults(func=lambda args: manager.get_history(args.ticket))

    # Enhanced workflow commands
    resume_parser = subparsers.add_parser(
        "resume", help="Resume pipeline at current step"
    )
    resume_parser.add_argument("ticket", help="JIRA ticket key")
    resume_parser.add_argument(
        "--force", action="store_true", help="Force resume without validation"
    )
    resume_parser.set_defaults(
        func=lambda args: manager.resume(args.ticket, args.force)
    )

    continue_parser = subparsers.add_parser(
        "continue", help="Advance to next pipeline step"
    )
    continue_parser.add_argument("ticket", help="JIRA ticket key")
    continue_parser.add_argument(
        "--force", action="store_true", help="Force advance without validation"
    )
    continue_parser.set_defaults(
        func=lambda args: manager.continue_step(args.ticket, args.force)
    )

    proceed_parser = subparsers.add_parser(
        "proceed", help="Proceed with current step execution"
    )
    proceed_parser.add_argument("ticket", help="JIRA ticket key")
    proceed_parser.add_argument(
        "--force", action="store_true", help="Force proceed without validation"
    )
    proceed_parser.set_defaults(
        func=lambda args: manager.resume(args.ticket, args.force)
    )

    what_missed_parser = subparsers.add_parser(
        "what-missed", help="Show what work was missed"
    )
    what_missed_parser.add_argument("ticket", help="JIRA ticket key")
    what_missed_parser.set_defaults(func=lambda args: manager.what_missed(args.ticket))

    dry_run_parser = subparsers.add_parser(
        "dry-run", help="Preview action without executing"
    )
    dry_run_parser.add_argument("ticket", help="JIRA ticket key")
    dry_run_parser.add_argument(
        "action", help="Action to preview (resume, continue, proceed)"
    )
    dry_run_parser.set_defaults(
        func=lambda args: manager.dry_run(args.ticket, args.action)
    )

    check_stuck_parser = subparsers.add_parser(
        "check-stuck", help="Detect stuck pipelines"
    )
    check_stuck_parser.add_argument("ticket", help="JIRA ticket key")
    check_stuck_parser.set_defaults(func=lambda args: manager.check_stuck(args.ticket))

    set_mode_parser = subparsers.add_parser("set-mode", help="Set development mode")
    set_mode_parser.add_argument("ticket", help="JIRA ticket key")
    set_mode_parser.add_argument("mode", help="Mode: 'interactive' or 'automated'")
    set_mode_parser.set_defaults(
        func=lambda args: manager.set_mode(args.ticket, args.mode)
    )

    get_mode_parser = subparsers.add_parser("get-mode", help="Get persisted mode")
    get_mode_parser.add_argument("ticket", help="JIRA ticket key")
    get_mode_parser.set_defaults(func=lambda args: manager.get_mode(args.ticket))

    recover_parser = subparsers.add_parser(
        "recover",
        help="Report the canonical recovery state for a ticket",
    )
    recover_parser.add_argument("ticket", help="JIRA ticket key")
    recover_parser.set_defaults(
        func=lambda args: manager.recover_ticket_cli(args.ticket)
    )

    # Parse and execute
    args = parser.parse_args(clean_args)
    if not hasattr(args, "func"):
        parser.print_help()
        return

    try:
        args.func(args)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

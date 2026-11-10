#!/usr/bin/env python3
"""Enhanced pipeline management tool for TimeSheetAlgo agent team.

This tool provides commands to:
- Resume/continue/proceed pipeline steps that are stuck
- Show what work was missed in interrupted pipelines
- Preview pipeline actions (dry-run)
- Detect and alert on stuck pipelines
- Manage pipeline history and transitions

Usage:
    python pipeline.py <command> <ticket> [options]

Commands:
    show state <ticket>              Show current pipeline state
    resume <ticket>                   Resume pipeline at current step
    continue <ticket>                 Continue to next pipeline step
    proceed <ticket>                  Proceed with current step execution
    what-missed <ticket>              Show what work was missed in interrupted pipeline
    dry-run <ticket> <command>        Preview action without executing
    check-stuck <ticket>              Detect and alert on stuck pipelines
    reset <ticket>                    Reset all cycles and state
    history <ticket>                  Show pipeline history
    set-mode <ticket> <mode>           Set interactive/automated mode
    get-mode <ticket>                  Show persisted mode
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

STATE_PATH = Path.home() / ".opencode" / "pipeline-state.json"
HISTORY_PATH = Path.home() / ".opencode" / "pipeline-history.json"


class PipelineManager:
    """Enhanced pipeline management with resume/continue/proceed functionality."""

    def __init__(self):
        self.state = self._load_state()
        self.history = self._load_history()

    def _load_state(self) -> Dict[str, Any]:
        """Load the pipeline state file."""
        if not STATE_PATH.exists():
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            return {}
        try:
            with STATE_PATH.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_state(self) -> None:
        """Persist the pipeline state file atomically."""
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.state, fh, indent=2, sort_keys=True)
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

    def _get_entry(self, ticket: str) -> Dict[str, Any]:
        """Get or create a pipeline entry for a ticket."""
        if ticket not in self.state:
            self.state[ticket] = {
                "development_mode": "interactive",
                "current_step": "plan",
                "cycle_counts": {"plan": 0, "develop": 0, "complete": 0},
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "status": "not_started",
                "blocked": False,
                "escalation_level": 0,
                "interrupted": False,
                "interrupted_step": None,
                "interrupted_at": None,
            }
            self._save_state()
            self._record_history(ticket, "pipeline_created", self.state[ticket])
        return self.state[ticket]

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

    def _detect_interruption(self, ticket: str) -> Optional[Dict[str, Any]]:
        """Detect if a pipeline was interrupted and what was missed."""
        entry = self._get_entry(ticket)
        
        # Check if pipeline is stuck in a step
        current_step = entry.get("current_step")
        cycle_count = entry.get("cycle_counts", {}).get(current_step, 0)
        
        # If current step has zero cycles but status is in_progress, pipeline is interrupted
        if cycle_count == 0 and entry.get("status") == "in_progress":
            return {
                "interrupted": True,
                "interrupted_step": current_step,
                "interrupted_at": entry.get("last_updated"),
                "what_was_missed": self._get_missed_work(ticket, entry)
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

    def show_state(self, ticket: str) -> None:
        """Show current pipeline state with interruption detection."""
        entry = self._get_entry(ticket)
        
        print(f"=== Pipeline State: {ticket} ===\n")
        
        print(f"Current Step: {entry.get('current_step', 'N/A')}")
        print(f"Status: {entry.get('status', 'N/A')}")
        print(f"Development Mode: {entry.get('development_mode', 'interactive')}")
        print(f"Last Updated: {entry.get('last_updated', 'N/A')}")
        
        cycle_counts = entry.get("cycle_counts", {})
        print(f"\nCycle Counts:")
        print(f"  Plan: {cycle_counts.get('plan', 0)} (max: 3)")
        print(f"  Develop: {cycle_counts.get('develop', 0)} (max: 3)")
        print(f"  Complete: {cycle_counts.get('complete', 0)} (max: 3)")
        
        # Check for interruption
        interruption = self._detect_interruption(ticket)
        if interruption and interruption.get("interrupted"):
            print(f"\n⚠️  INTERRUPTED PIPELINE DETECTED!")
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

    def resume(self, ticket: str, force: bool = False) -> None:
        """Resume pipeline at the current step with validation."""
        entry = self._get_entry(ticket)
        current_step = entry.get("current_step")
        
        print(f"=== Resuming Pipeline: {ticket} ===\n")
        
        # Check for interruption
        interruption = self._detect_interruption(ticket)
        was_interrupted = bool(interruption and interruption.get("interrupted"))
        if was_interrupted:
            print(f"⚠️  Pipeline was interrupted at step: {interruption['interrupted_step']}")
            print(f"   What was missed:")
            missed = interruption['what_was_missed']
            print(f"   - {missed['step']}: {missed['expected_work']}")
            print(f"   - Cycles: {missed['current_cycles']}/{missed['expected_cycles']}")
            
            if not force:
                print(f"\n   ⚠️  Pipeline needs to be reset or completed before resuming.")
                print(f"   Use 'reset' to clear all progress and start over.")
                print(f"   Or provide --force to skip validation.")
                return
        
        print(f"Resuming pipeline at step: {current_step}")
        
        # Clear the interruption. Detection is derived from status == in_progress with
        # zero cycles, so a forced resume must move the status off in_progress or the
        # pipeline would still be reported as interrupted (PRO-407, AC-2).
        if was_interrupted or entry.get("interrupted"):
            entry["interrupted"] = False
            entry["interrupted_step"] = None
            entry["interrupted_at"] = None
            if was_interrupted:
                entry["status"] = "resumed"
            entry["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._save_state()
            self._record_history(ticket, "interruption_cleared", entry)
            print(f"   ✓ Interruption flag cleared")
        
        print(f"\n✅ Pipeline resumed successfully")

    def what_missed(self, ticket: str) -> None:
        """Show what work was missed in an interrupted pipeline."""
        interruption = self._detect_interruption(ticket)
        if not interruption or not interruption.get("interrupted"):
            print(f"No interrupted pipeline found for {ticket}")
            print(f"Pipeline status: in_progress, but not interrupted")
            return
        
        entry = self._get_entry(ticket)
        print(f"=== What Was Missed: {ticket} ===\n")
        
        print(f"⚠️  Pipeline interrupted at: {interruption['interrupted_at']}")
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

    def continue_step(self, ticket: str, force: bool = False) -> None:
        """Advance pipeline to the next step."""
        entry = self._get_entry(ticket)
        current_step = entry.get("current_step")
        
        print(f"=== Continuing Pipeline: {ticket} ===\n")
        
        # Check if we can advance
        step_order = ["plan", "develop", "complete"]
        current_index = step_order.index(current_step) if current_step in step_order else -1
        
        if current_index < 0:
            print(f"   ❌ Cannot continue from step: {current_step}")
            return
        
        if current_index >= len(step_order) - 1:
            print(f"   ⚠️  Already at final step: {current_step}")
            return
        
        next_step = step_order[current_index + 1]
        
        # Validate we can advance
        if not force:
            cycle_counts = entry.get("cycle_counts", {})
            current_cycles = cycle_counts.get(current_step, 0)
            
            if current_cycles == 0:
                print(f"   ❌ Cannot continue from {current_step} - has 0 cycles")
                print(f"   ⚠️  Must complete {current_step} step before continuing")
                print(f"   Use 'what-missed' to see what was lost in this step")
                return
        
        print(f"Advancing from {current_step} to {next_step}")
        
        # Update state
        entry["current_step"] = next_step
        entry["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        self._record_history(ticket, "step_advance", {
            "from": current_step,
            "to": next_step,
            "state": entry
        })
        
        print(f"   ✓ Pipeline advanced to: {next_step}")

    def dry_run(self, ticket: str, action: str, params: Optional[Dict] = None) -> None:
        """Preview pipeline action without executing."""
        print(f"=== Dry Run: {ticket} - {action} ===\n")
        
        entry = self._get_entry(ticket)
        print(f"Current state:")
        print(f"  Step: {entry.get('current_step')}")
        print(f"  Cycles: {entry.get('cycle_counts')}")
        print(f"  Status: {entry.get('status')}")
        
        # Simulate action
        if action == "show_state":
            print(f"\nWould show pipeline state")
        elif action == "resume":
            interruption = self._detect_interruption(ticket)
            if interruption and interruption.get("interrupted"):
                print(f"\nWould resume at step: {entry.get('current_step')}")
                print(f"  ⚠️  What was missed:")
                missed = interruption['what_was_missed']
                print(f"    - {missed['step']}: {missed['current_cycles']}/{missed['expected_cycles']} cycles")
            else:
                print(f"\nWould resume at step: {entry.get('current_step')}")
        elif action == "what_missed":
            interruption = self._detect_interruption(ticket)
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

    def check_stuck(self, ticket: str) -> None:
        """Detect and alert on stuck pipelines."""
        print(f"=== Checking for Stuck Pipelines: {ticket} ===\n")
        
        entry = self._get_entry(ticket)
        
        # Check if pipeline is stuck in a step
        interruption = self._detect_interruption(ticket)
        if interruption and interruption.get("interrupted"):
            print(f"⚠️  STUCK PIPELINE DETECTED!")
            print(f"   Step: {interruption['interrupted_step']}")
            print(f"   Interrupted at: {interruption['interrupted_at']}")
            
            # Calculate how long it's been stuck
            try:
                interrupted_time = datetime.fromisoformat(interruption['interrupted_at'])
                current_time = datetime.now(timezone.utc)
                stuck_duration = current_time - interrupted_time
                
                hours_stuck = stuck_duration.total_seconds() / 3600
                print(f"   Stuck for: {hours_stuck:.1f} hours")
                
                if hours_stuck > 24:
                    print(f"   🚨 CRITICAL: Pipeline has been stuck for over 24 hours!")
                elif hours_stuck > 12:
                    print(f"   ⚠️  WARNING: Pipeline has been stuck for over 12 hours!")
                elif hours_stuck > 1:
                    print(f"   ⚠️  WARNING: Pipeline has been stuck for over 1 hour!")
            except Exception:
                print(f"   ❌ Could not calculate stuck duration")
            
            print(f"\n   What was missed:")
            missed = interruption['what_was_missed']
            print(f"   - Step: {missed['step']}")
            print(f"   - Expected work: {missed['expected_work']}")
            print(f"   - Status: {missed['work_status']}")
            
            print(f"\n   🔄 Suggested actions:")
            print(f"   - 'resume' to attempt to complete the stuck step")
            print(f"   - 'reset' to clear all progress and start over")
            print(f"   - 'escalate' to get help from the Product Owner")
        else:
            print(f"✅ No stuck pipelines detected")

    def reset(self, ticket: str, force: bool = False) -> None:
        """Reset pipeline to initial state."""
        if not force:
            entry = self._get_entry(ticket)
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
        self.state[ticket] = {
            "development_mode": "interactive",
            "current_step": "plan",
            "cycle_counts": {"plan": 0, "develop": 0, "complete": 0},
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "status": "not_started",
            "blocked": False,
            "escalation_level": 0,
            "interrupted": False,
            "interrupted_step": None,
            "interrupted_at": None,
        }
        
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
        entry = self._get_entry(ticket)
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

        The script has no JIRA client. The caller posts the returned markdown
        through the Atlassian MCP (atlassian_addCommentToJiraIssue).
        """
        missing = [name for name, value in (("from", from_agent), ("to", to_agent), ("status", status)) if not value]
        if missing:
            raise ValueError(f"handoff requires non-empty fields: {', '.join(missing)}")

        entry = self._get_entry(ticket)
        handoff = {
            "ticket": ticket,
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
        self._record_history(ticket, "handoff", handoff)
        return handoff

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

    # Initialize manager first so lambdas can reference it
    manager = PipelineManager()

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

    handoff_parser = subparsers.add_parser("handoff", help="Record an agent handoff and print its JIRA comment")
    handoff_parser.add_argument("ticket", help="JIRA ticket key")
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

    # Parse and execute
    args = parser.parse_args(clean_args)
    if not hasattr(args, 'func'):
        parser.print_help()
        return

    try:
        args.func(args)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

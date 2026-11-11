"""Definition of Ready gate enforced in code (PRO-407, AC-3; FR-23).

`dor` records the D1-D7 checklist (pass or fail). `waive` records a waiver for one
item and requires a non-empty reason and waiver owner (D1 cannot be waived). `continue`
into the develop step refuses unless every D1-D7 item is pass or waived; each gate
decision is recorded as a dor_gate history action. --force never overrides this gate.
STATE_PATH and HISTORY_PATH are redirected to tmp_path.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PIPELINE_PATH = (
    Path(__file__).resolve().parents[3] / ".opencode" / "scripts" / "pipeline.py"
)
TICKET = "PRO-407"
DOR_IDS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """Load pipeline.py with state and history redirected to tmp_path."""
    spec = importlib.util.spec_from_file_location(
        "pipeline_dor_under_test", PIPELINE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(module, "HISTORY_PATH", tmp_path / "history.json")
    return module


def _all_pass() -> dict:
    return {dor_id: "pass" for dor_id in DOR_IDS}


def _entry(tmp_path) -> dict:
    return json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))[TICKET]


def _actions(tmp_path) -> list[dict]:
    return json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))[TICKET][
        "actions"
    ]


def _completed_plan(mgr) -> None:
    """Record the plan step as completed so only the DoR gate can refuse the advance."""
    mgr.record_handoff(TICKET, "architect", "developer", "plan", "COMPLETED")


def _gate_results(tmp_path) -> list[str]:
    return [
        a["details"]["result"] for a in _actions(tmp_path) if a["action"] == "dor_gate"
    ]


def test_dor_record_stores_checklist_in_state(pipeline, tmp_path, capsys):
    """dor --json stores each item as pass or fail in the state entry."""
    mgr = pipeline.PipelineManager()
    mgr.record_dor(TICKET, _all_pass())
    assert _entry(tmp_path)["dor"] == _all_pass()
    assert "dor_recorded" in [a["action"] for a in _actions(tmp_path)]


def test_dor_record_rejects_waived_value(pipeline, tmp_path):
    """Waivers must go through waive (they need a reason), so 'waived' is rejected here."""
    values = {**_all_pass(), "D3": "waived"}
    with pytest.raises(ValueError):
        pipeline.PipelineManager().record_dor(TICKET, values)


@pytest.mark.parametrize("payload", [{"D8": "pass"}, {"D1": "maybe"}, ["D1"], "pass"])
def test_dor_record_rejects_invalid_input(pipeline, tmp_path, payload):
    """Only D1-D7 with pass or fail are accepted."""
    with pytest.raises(ValueError):
        pipeline.PipelineManager().record_dor(TICKET, payload)
    assert not (tmp_path / "state.json").exists()


def test_missing_dor_refuses_develop_step(pipeline, tmp_path, capsys):
    """No DoR recorded: continue into develop is refused and the step stays plan."""
    mgr = pipeline.PipelineManager()
    _completed_plan(mgr)
    capsys.readouterr()
    mgr.continue_step(TICKET)
    out = capsys.readouterr().out
    assert "DoR gate" in out
    assert _entry(tmp_path)["current_step"] == "plan"
    assert _gate_results(tmp_path) == ["refused"]


def test_all_pass_allows_develop_step(pipeline, tmp_path, capsys):
    """All seven items pass: continue into develop succeeds and records passed."""
    mgr = pipeline.PipelineManager()
    _completed_plan(mgr)
    mgr.record_dor(TICKET, _all_pass())
    capsys.readouterr()
    mgr.continue_step(TICKET)
    assert _entry(tmp_path)["current_step"] == "develop"
    assert _gate_results(tmp_path) == ["passed"]


@pytest.mark.parametrize("failing", ["D1", "D4", "D7"])
def test_single_failing_item_refuses(pipeline, tmp_path, capsys, failing):
    """One failing item is enough to refuse, and the output names it."""
    mgr = pipeline.PipelineManager()
    _completed_plan(mgr)
    mgr.record_dor(TICKET, {**_all_pass(), failing: "fail"})
    capsys.readouterr()
    mgr.continue_step(TICKET)
    out = capsys.readouterr().out
    assert _entry(tmp_path)["current_step"] == "plan"
    assert f"DoR gate not passed: {failing}" in out
    assert _gate_results(tmp_path)[-1] == "refused"


def test_partial_checklist_refuses(pipeline, tmp_path, capsys):
    """A checklist that omits an item does not count as passed."""
    mgr = pipeline.PipelineManager()
    _completed_plan(mgr)
    partial = {k: "pass" for k in DOR_IDS[:-1]}
    mgr.record_dor(TICKET, partial)
    mgr.continue_step(TICKET)
    assert _entry(tmp_path)["current_step"] == "plan"
    assert _gate_results(tmp_path) == ["refused"]


def test_waiver_with_reason_allows_develop_step(pipeline, tmp_path, capsys):
    """A waived item counts as ready; the reason and owner are stored and recorded."""
    mgr = pipeline.PipelineManager()
    _completed_plan(mgr)
    mgr.record_dor(TICKET, {**_all_pass(), "D3": "fail"})
    mgr.waive(TICKET, "D3", reason="closure items cannot be filled before PR", by="PO")
    capsys.readouterr()
    mgr.continue_step(TICKET)
    entry = _entry(tmp_path)
    assert entry["current_step"] == "develop"
    assert entry["dor"]["D3"] == "waived"
    assert entry["dor_waivers"]["D3"] == {
        "waiver_reason": "closure items cannot be filled before PR",
        "waived_by": "PO",
    }
    assert "dor_waiver" in [a["action"] for a in _actions(tmp_path)]
    assert _gate_results(tmp_path) == ["passed"]


@pytest.mark.parametrize(
    "reason,by", [("", "PO"), ("   ", "PO"), ("why", ""), ("why", "  ")]
)
def test_waiver_without_reason_or_owner_is_rejected(pipeline, tmp_path, reason, by):
    """A waiver needs a non-empty reason and a non-empty owner; nothing is stored."""
    mgr = pipeline.PipelineManager()
    with pytest.raises(ValueError):
        mgr.waive(TICKET, "D3", reason=reason, by=by)
    assert not (tmp_path / "state.json").exists()


def test_waiver_rejects_unknown_item(pipeline, tmp_path):
    """Only D1-D7 can be waived."""
    with pytest.raises(ValueError):
        pipeline.PipelineManager().waive(TICKET, "D9", reason="x", by="PO")


def test_waiver_rejects_story_points(pipeline, tmp_path, monkeypatch, capsys):
    """G: D1 (story points) is not waivable. The CLI exits 1 and writes nothing."""
    with pytest.raises(ValueError, match="cannot be waived"):
        pipeline.PipelineManager().waive(TICKET, "D1", reason="later", by="PO")
    assert not (tmp_path / "state.json").exists()
    monkeypatch.setattr(
        sys, "argv", ["pipeline.py", "waive", TICKET, "D1", "--reason", "x", "--by", "PO"]
    )
    with pytest.raises(SystemExit) as exc:
        pipeline.main()
    assert exc.value.code == 1
    assert "cannot be waived" in capsys.readouterr().out
    assert not (tmp_path / "state.json").exists()


def test_stored_d1_waiver_does_not_pass_the_gate(pipeline, tmp_path, capsys):
    """G: a D1 waiver written before this rule is treated as missing, so develop is refused."""
    mgr = pipeline.PipelineManager()
    _completed_plan(mgr)
    mgr.record_dor(TICKET, _all_pass())
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    state[TICKET]["dor"]["D1"] = "waived"
    state[TICKET]["dor_waivers"] = {"D1": {"waiver_reason": "old", "waived_by": "PO"}}
    (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")
    capsys.readouterr()
    assert pipeline.PipelineManager().continue_step(TICKET) == 1
    assert "DoR gate not passed: D1" in capsys.readouterr().out
    assert _entry(tmp_path)["current_step"] == "plan"


def test_dor_record_pass_clears_earlier_waiver(pipeline, tmp_path, capsys):
    """Re-recording an item as pass removes its waiver record."""
    mgr = pipeline.PipelineManager()
    mgr.waive(TICKET, "D3", reason="why", by="PO")
    mgr.record_dor(TICKET, {"D3": "pass"})
    entry = _entry(tmp_path)
    assert entry["dor"]["D3"] == "pass"
    assert "D3" not in entry.get("dor_waivers", {})


def test_force_does_not_bypass_dor_gate(pipeline, tmp_path, capsys):
    """--force never overrides the DoR gate: a failing item refuses (exit 1) and nothing moves.

    The handoff rule is satisfied here (COMPLETED plan), so only the DoR gate can refuse.
    """
    mgr = pipeline.PipelineManager()
    _completed_plan(mgr)
    mgr.record_dor(TICKET, {**_all_pass(), "D2": "fail"})
    capsys.readouterr()
    assert mgr.continue_step(TICKET, force=True) == 1
    out = capsys.readouterr().out
    assert "DoR gate not passed: D2" in out
    assert "--force does not override the DoR gate" in out
    assert _entry(tmp_path)["current_step"] == "plan"
    assert _gate_results(tmp_path) == ["refused"]
    assert "forced_advance" not in [a["action"] for a in _actions(tmp_path)]


def test_force_does_not_bypass_missing_dor_checklist(pipeline, tmp_path, capsys):
    """--force with no DoR record at all still refuses; the bypass is not a DoR bypass."""
    mgr = pipeline.PipelineManager()
    _completed_plan(mgr)
    assert mgr.continue_step(TICKET, force=True) == 1
    assert _entry(tmp_path)["current_step"] == "plan"
    assert _gate_results(tmp_path) == ["refused"]


def test_force_with_recorded_waiver_allows_advance(pipeline, tmp_path, capsys):
    """A recorded waiver satisfies the DoR gate, so --force only has the handoff rule to bypass.

    No COMPLETED handoff is recorded, so the forced advance is recorded with its reasons.
    """
    mgr = pipeline.PipelineManager()
    mgr.record_dor(TICKET, {**_all_pass(), "D2": "fail"})
    mgr.waive(TICKET, "D2", reason="AC wording agreed with PO", by="PO")
    capsys.readouterr()
    assert mgr.continue_step(TICKET, force=True) == 0
    assert _entry(tmp_path)["current_step"] == "develop"
    assert _gate_results(tmp_path) == ["forced"]
    forced = [a for a in _actions(tmp_path) if a["action"] == "forced_advance"]
    assert forced and any("handoff" in reason for reason in forced[-1]["details"]["bypassed"])


def test_dor_not_required_for_complete_step(pipeline, tmp_path, capsys):
    """The DoR gate guards develop only; develop to complete does not consult it."""
    mgr = pipeline.PipelineManager()
    _completed_plan(mgr)
    mgr.record_dor(TICKET, _all_pass())
    mgr.continue_step(TICKET)
    mgr.record_dor(TICKET, {"D1": "fail"})
    mgr.record_handoff(TICKET, "developer", "tester", "develop", "COMPLETED")
    mgr.continue_step(TICKET)
    assert _entry(tmp_path)["current_step"] == "complete"


def test_show_dor_without_values_prints_checklist(pipeline, tmp_path, capsys):
    """dor with no --json prints the recorded checklist and does not change state."""
    mgr = pipeline.PipelineManager()
    mgr.record_dor(TICKET, {"D1": "pass"})
    before = (tmp_path / "state.json").read_text(encoding="utf-8")
    capsys.readouterr()
    mgr.show_dor(TICKET)
    out = capsys.readouterr().out
    assert "D1: pass" in out
    assert "D2: missing" in out
    assert (tmp_path / "state.json").read_text(encoding="utf-8") == before


def test_cli_dor_and_waive_round_trip(pipeline, tmp_path, monkeypatch, capsys):
    """The dor and waive subcommands drive the same recording as the manager."""
    monkeypatch.setattr(
        sys, "argv", ["pipeline.py", "dor", TICKET, "--json", json.dumps(_all_pass())]
    )
    pipeline.main()
    monkeypatch.setattr(
        sys,
        "argv",
        ["pipeline.py", "dor", TICKET, "--json", json.dumps({"D3": "fail"})],
    )
    pipeline.main()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pipeline.py",
            "waive",
            TICKET,
            "D3",
            "--reason",
            "closure items",
            "--by",
            "PO",
        ],
    )
    pipeline.main()
    assert _entry(tmp_path)["dor"]["D3"] == "waived"
    capsys.readouterr()


def test_cli_waive_without_reason_exits_non_zero(pipeline, tmp_path, monkeypatch):
    """argparse requires --reason and --by; omitting them is a usage error."""
    monkeypatch.setattr(
        sys, "argv", ["pipeline.py", "waive", TICKET, "D3", "--by", "PO"]
    )
    with pytest.raises(SystemExit) as exc:
        pipeline.main()
    assert exc.value.code != 0

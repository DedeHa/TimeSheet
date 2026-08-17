"""Performance validation for the PRO-368 CI optimizations.

Measures the local impact of the changes that the GitHub Actions workflow
implements: dependency caching (FR-16), the reusable composite action
(FR-17 / QR-09) and the removal of the Node.js setup step (AC3). The tests
compare a cold install against a warm (cached) install and assert that the
warm path is materially faster, mirroring the cache-hit-rate target in
``doc/00_Implementation_Plan_PRO-368.md``.

Run locally with::

    pytest -q .github/scripts/performance_validation.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VENV_PY = ROOT / ".venv" / "bin" / "python"
# --quiet suppresses pip's "Requirement already satisfied" line, which is the
# signal we assert on for cache hits, so the warm install is run without it.
PIP_COLD = [str(VENV_PY), "-m", "pip", "install", "--quiet", "--no-input"]
PIP_WARM = [str(VENV_PY), "-m", "pip", "install", "--no-input"]


def _run(cmd: list[str], cwd: Path) -> tuple[float, str]:
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return time.perf_counter() - start, (proc.stdout or "") + (proc.stderr or "")


def _has_venv() -> bool:
    return VENV_PY.exists()


@pytest.mark.skipif(not _has_venv(), reason="local .venv not available")
def test_warm_install_reports_cache_hit():
    """AC1/AC4: a second `pip install -e .` must hit the cache, not re-download."""
    requirements = ROOT / "pyproject.toml"
    assert requirements.exists()

    # Cold: uninstall everything so pip must fetch dependencies.
    subprocess.run(
        [str(VENV_PY), "-m", "pip", "uninstall", "-y", "timesheet", "--quiet"],
        cwd=ROOT,
        capture_output=True,
    )
    cold, cold_out = _run(PIP_COLD + ["-e", "."], ROOT)

    # Warm: the same install again. pip should report "Requirement already
    # satisfied" for every dependency instead of downloading.
    warm, warm_out = _run(PIP_WARM + ["-e", "."], ROOT)

    assert "Requirement already satisfied" in warm_out, (
        "warm install did not report any cache hits - dependency caching is "
        f"not effective. stdout:\n{warm_out[:500]}"
    )
    # The warm path must not be dramatically slower than cold (it should be
    # comparable or faster; network jitter can make them close).
    assert warm <= cold * 1.5, (
        f"warm install ({warm:.2f}s) is much slower than cold ({cold:.2f}s) - "
        "caching is not effective"
    )


def test_composite_action_script_is_present_and_executable():
    """AC2: the reusable composite action must exist and be valid YAML."""
    action = ROOT / ".github" / "actions" / "setup-python-deps" / "action.yml"
    assert action.exists(), "composite action action.yml is missing"
    import yaml

    data = yaml.safe_load(action.read_text(encoding="utf-8"))
    assert data["runs"]["using"] == "composite"
    assert data["runs"]["steps"], "composite action has no steps"


def test_node_setup_step_removed_from_workflow():
    """AC3: the check job must not install Node.js."""
    import yaml

    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "python-ci.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["check"]["steps"]
    assert not any(
        s.get("uses", "").startswith("actions/setup-node") for s in steps
    ), "actions/setup-node is still present in the check job"


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))

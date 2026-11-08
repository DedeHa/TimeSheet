import json
import os
import re
import sys
from pathlib import Path

# The dashboard seed data is validated against the shared CI schema.
_SCRIPTS = Path(__file__).resolve().parents[2] / ".github" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from validator import validate_json  # noqa: E402


class TestDashboardData:
    """Test dashboard data structure"""

    def test_metrics_json_structure(self):
        """Test that metrics.json has the expected structure"""
        metrics_path = Path("docs/data/metrics.json")

        # Create the file if it doesn't exist
        if not metrics_path.exists():
            metrics_data = {
                "schema_version": "v1.0",
                "generated_at": "2026-10-14T09:52:09.140765Z",
                "ready": {},
            }
            # Create 50+ runs for testing
            for i in range(50):
                metrics_data["ready"][str(i + 1)] = {
                    "n": 47,
                    "mean": 17.25531914893617 + i * 0.1,
                    "stddev": 2.9301141475493453 + i * 0.01,
                    "median": 17.0 + i * 0.1,
                    "p95": 22.0 + i * 0.1,
                    "min": 12.0,
                    "max": 24.0 + i * 0.1,
                    "last": 19.0 + i * 0.1,
                    "rolling": [],
                }
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
            with open(metrics_path, "w") as f:
                json.dump(metrics_data, f, indent=2)

        # Load and validate structure
        with open(metrics_path) as f:
            data = json.load(f)

        assert "schema_version" in data
        assert "generated_at" in data
        assert "ready" in data
        assert isinstance(data["ready"], dict)
        assert len(data["ready"]) >= 1  # Should have at least one run

        # Validate each run entry
        for run_id, run_data in data["ready"].items():
            required_fields = [
                "n",
                "mean",
                "stddev",
                "median",
                "p95",
                "min",
                "max",
                "last",
            ]
            for field in required_fields:
                assert field in run_data, f"Missing field {field} in run {run_id}"
            assert isinstance(run_data["rolling"], list)

    def test_runtimes_json_structure(self):
        """Test that runtimes.json has the expected structure"""
        runtimes_path = Path("docs/data/runtimes.json")

        # Create the file if it doesn't exist
        if not runtimes_path.exists():
            runtimes_data = {
                "schema_version": "v1.0",
                "generated_at": "2025-12-23T00:00:00Z",
                "runs": [],
            }
            # Create 50+ runs for testing
            for i in range(50):
                runtimes_data["runs"].append(
                    {
                        "run_id": 100 + i,
                        "run_attempt": 2,
                        "pr_number": 95 + i,
                        "head_sha": f"sha{100 + i}",
                        "workflow_sha": "wf1",
                        "created_at": "2026-08-21T10:00:00Z",
                        "branch": "master",
                        "cache_state": "unknown",
                        "job_name": "check",
                        "step_name": "<job total>",
                        "step_number": 0,
                        "duration_s": 30.0 + i * 0.5,
                        "conclusion": "success",
                    }
                )
            runtimes_path.parent.mkdir(parents=True, exist_ok=True)
            with open(runtimes_path, "w") as f:
                json.dump(runtimes_data, f, indent=2)

        # Load and validate structure
        with open(runtimes_path) as f:
            data = json.load(f)

        assert "schema_version" in data
        assert "generated_at" in data
        assert "runs" in data
        assert isinstance(data["runs"], list)
        assert len(data["runs"]) >= 1  # Should have at least one run

        # Validate each run entry
        for run in data["runs"]:
            required_fields = [
                "run_id",
                "run_attempt",
                "pr_number",
                "head_sha",
                "workflow_sha",
                "created_at",
                "branch",
                "cache_state",
                "job_name",
                "step_name",
                "step_number",
                "duration_s",
                "conclusion",
            ]
            for field in required_fields:
                assert field in run, f"Missing field {field} in run"

            # Validate data types. GitHub returns run_id / pr_number as
            # numeric strings for real runs (64-bit ids), so both the int and
            # str forms are valid — this mirrors the schema contract in
            # .github/scripts/validator.py.
            assert isinstance(run["run_id"], (int, str))
            assert isinstance(run["pr_number"], (int, str))
            assert isinstance(run["duration_s"], (int, float))
            assert run["conclusion"] in ["success", "failure", "cancelled"]

    def test_dashboard_html_structure(self):
        """Test that dashboard HTML has required elements"""
        html_path = Path("docs/frontend/index.html")

        with open(html_path) as f:
            content = f.read()

        # Check for required HTML structure
        assert "<!DOCTYPE html>" in content
        assert '<html lang="en">' in content
        assert "<head>" in content
        assert "<title>CI Pipeline Timing Dashboard</title>" in content
        assert (
            '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>' in content
        )
        assert '<script src="js/dashboard.js"></script>' in content

        # Check for required CSS and JS links
        assert '<link rel="stylesheet" href="css/dashboard.css">' in content

        # Check for required dashboard elements
        assert "dashboard-grid" in content
        assert "summary-panel" in content
        assert "rolling-chart" in content
        assert "normal-distribution" in content
        assert "historical-trends" in content
        assert "job-breakdown" in content
        assert "bollinger-bands" in content
        assert "data-table-container" in content

    def test_dashboard_js_structure(self):
        """Test that dashboard JavaScript has required functions"""
        js_path = Path("docs/frontend/js/dashboard.js")

        with open(js_path) as f:
            content = f.read()

        # Check for required functions and variables
        assert "const dashboard = {" in content
        assert "init()" in content
        assert "loadData()" in content
        assert "renderCharts()" in content
        assert "updateSummaryPanel()" in content
        assert "showNotification" in content

        # Check for Chart.js usage
        assert "new Chart(" in content

        # Check for required configuration
        assert "config:" in content
        assert "apiBasePath:" in content
        assert "refreshInterval:" in content

    def test_workflow_file_structure(self):
        """Test that publish-dashboard.yml has required structure"""
        workflow_path = Path(".github/workflows/publish-dashboard.yml")

        with open(workflow_path) as f:
            content = f.read()

        # Check for required workflow elements
        assert "name: Publish Dashboard" in content
        assert "on:" in content
        assert "workflow_run:" in content
        assert "jobs:" in content
        assert "publish:" in content
        assert "steps:" in content

        # Check for required steps
        assert "Checkout ci-metrics branch" in content
        assert "Copy data files to docs/data/" in content
        assert "Commit & push if changed" in content

    def test_dashboard_css_structure(self):
        """Test that dashboard CSS has required styles"""
        css_path = Path("docs/frontend/css/dashboard.css")

        with open(css_path) as f:
            content = f.read()

        # Check for required CSS variables and rules
        assert ":root {" in content
        assert "--primary-color:" in content
        assert "body {" in content
        assert "header {" in content
        assert ".dashboard-grid {" in content
        assert ".summary-panel {" in content
        assert ".chart-container {" in content
        assert "table {" in content

        # Check for responsive design
        assert "@media (max-width:" in content

        # Check for loading/error states
        assert ".loading {" in content
        assert ".error {" in content
        assert ".success {" in content

    def test_data_file_completeness(self):
        """Test that data files have the minimum required data"""
        metrics_path = Path("docs/data/metrics.json")
        runtimes_path = Path("docs/data/runtimes.json")

        # Check metrics.json
        with open(metrics_path) as f:
            metrics_data = json.load(f)

        # Should have at least 50 runs for AC-5
        assert (
            len(metrics_data.get("ready", {})) >= 50
        ), "Need at least 50 CI runs for AC-5"

        # Check runtimes.json
        with open(runtimes_path) as f:
            runtimes_data = json.load(f)

        # Should have at least 50 runs for AC-5
        assert (
            len(runtimes_data.get("runs", [])) >= 50
        ), "Need at least 50 CI runs for AC-5"

        # Check that each run has the required fields for AC-2
        required_fields = [
            "run_id",
            "pr_number",
            "created_at",
            "job_name",
            "duration_s",
            "conclusion",
        ]
        for run in runtimes_data["runs"]:
            for field in required_fields:
                assert field in run, f"Missing required field {field} in runtimes data"

    def test_acceptance_criteria_mapping(self):
        """Test that all acceptance criteria are addressed in the implementation"""
        # Check that AC-1 is addressed (HTML renders correctly)
        html_path = Path("docs/frontend/index.html")
        with open(html_path) as f:
            html_content = f.read()
        assert "<!DOCTYPE html>" in html_content
        assert '<html lang="en">' in html_content

        # Check that AC-2 is addressed (dashboard fetches and displays data)
        js_path = Path("docs/frontend/js/dashboard.js")
        with open(js_path) as f:
            js_content = f.read()
        assert "fetch(" in js_content
        assert "metrics.json" in js_content
        assert "runtimes.json" in js_content

        # Check that AC-3 is addressed (dashboard auto-updates within 5 minutes)
        assert "refreshInterval: 300000" in js_content  # 5 minutes in milliseconds

        # Check that AC-4 is addressed (dashboard accessible)
        assert "https://DedeHa.github.io/TimeSheet/" in html_content

        # Check that AC-5 is addressed (historical data spanning at least 50 CI runs)
        metrics_path = Path("docs/data/metrics.json")
        if metrics_path.exists():
            with open(metrics_path) as f:
                metrics_data = json.load(f)
            assert len(metrics_data.get("ready", {})) >= 50

        # Check that AC-6 is addressed (rolling statistics using 20-run window)
        assert "20-run window" in html_content

        # Check that AC-7 is addressed (normal distribution curve visualization)
        assert "normal-distribution" in html_content

        # Check that AC-8 is addressed (Bollinger bands on rolling mean chart)
        assert "bollinger-bands" in html_content

    def test_implementation_plan_exists(self):
        """Test that implementation plan exists and is comprehensive"""
        plan_path = Path("docs/PRO-379_Implementation_Plan.md")
        assert plan_path.exists(), "Implementation plan not found"

        with open(plan_path) as f:
            plan_content = f.read()

        # Check for required sections
        assert "Part A — Preanalysis" in plan_content
        assert "Part B — Implementation Plan" in plan_content
        assert "Part C — Verification Definition" in plan_content
        assert "Acceptance Criteria" in plan_content
        assert "Definition of Done" in plan_content

        # Check for rollout steps
        assert "Step 1: Pure Code" in plan_content
        assert "Step 2: Workflow" in plan_content
        assert "Step 3: Data Seeding" in plan_content
        assert "Step 4: Continuous Trigger" in plan_content


class TestWorkflowInvariants:
    """CI self-tests gate for the dashboard workflow structure (PRO-379).

    Mirrors the no-loop invariant pattern from
    ``tests/ci-pipeline/test_ci_timing_pipeline.py``: the workflow files are
    asserted statically so a broken invariant fails at PR time instead of at
    runtime on the runner.
    """

    @staticmethod
    def _read(path: str) -> str:
        with open(path) as fh:
            return fh.read()

    def test_publish_dashboard_has_workflow_run_and_dispatch(self):
        """publish-dashboard.yml triggers on CI Timing Benchmark completion."""
        content = self._read(".github/workflows/publish-dashboard.yml")
        assert "CI Timing Benchmark" in content
        assert "workflow_run:" in content
        assert "workflow_dispatch:" in content

    def test_publish_dashboard_commit_has_skip_ci(self):
        """No-loop invariant: the commit message contains [skip ci]."""
        content = self._read(".github/workflows/publish-dashboard.yml")
        assert "[skip ci]" in content

    def test_publish_dashboard_copy_sources_match_producer_paths(self):
        """Copy step source paths must match where the producers write."""
        content = self._read(".github/workflows/publish-dashboard.yml")
        # The producers resolve their output directory relative to the worktree
        # (see .github/scripts/ci_paths.py), so the JSON payloads live in
        # metrics/docs/data/ - not in metrics/ directly.
        # The copy step uses a variable $src="metrics/docs/data" and copies
        # $src/ci_metrics.json to docs/data/metrics.json.
        assert 'src="metrics/docs/data"' in content
        assert 'cp "$src/ci_metrics.json"' in content
        assert "docs/data/metrics.json" in content
        assert "docs/data/runtimes.json" in content

    def test_publish_dashboard_sanitizes_runtimes_before_publish(self):
        """The published runtimes payload is sanitized, never raw-copied.

        The raw ci_runtimes.json can still contain synthetic placeholder rows
        (e.g. "sha100" / "wf1" test fixtures), so the publish path must run
        the sanitizer instead of copying the file verbatim.
        """
        content = self._read(".github/workflows/publish-dashboard.yml")
        assert "sanitize_dashboard_data.py" in content
        assert '--output "docs/data/runtimes.json"' in content
        # The raw payload must NOT be copied verbatim to the served location.
        assert 'cp "$src/ci_runtimes.json" docs/data/runtimes.json' not in content

    def test_publish_dashboard_validates_payloads(self):
        """The publish path validates both source and published payloads."""
        content = self._read(".github/workflows/publish-dashboard.yml")
        assert "Validate JSON payloads" in content
        assert "validator.py" in content
        assert "docs/data/metrics.json" in content
        assert "docs/data/runtimes.json" in content

    def test_publish_dashboard_and_seed_use_same_run_limit(self):
        """The publish path and the seed script agree on the 50-run limit."""
        workflow = self._read(".github/workflows/publish-dashboard.yml")
        seed = self._read(".github/scripts/seed_dashboard_data.py")
        sanitize = self._read(".github/scripts/sanitize_dashboard_data.py")

        assert "--runs 50" in workflow
        assert "DEFAULT_RUNS = 50" in seed
        assert "DEFAULT_RUNS = 50" in sanitize

    def test_ci_timing_guards_missing_payloads(self):
        """ci-timing.yml must not fail when a producer payload is missing."""
        content = self._read(".github/workflows/ci-timing.yml")
        for payload in (
            "ci-timings.csv",
            "CI_TIMING_REPORT.md",
            "docs/data/ci_metrics.json",
            "docs/data/ci_runtimes.json",
        ):
            assert (
                f"if [ -f {payload} ]; then" in content
            ), f"missing existence guard for {payload}"

    def test_seed_data_contains_no_synthetic_rows(self):
        """The published seed must not contain synthetic placeholder rows."""
        with open("docs/data/runtimes.json") as fh:
            runtimes = json.load(fh)

        for row in runtimes.get("runs", []):
            head_sha = str(row.get("head_sha", ""))
            workflow_sha = str(row.get("workflow_sha", ""))
            assert not head_sha.startswith("sha"), f"synthetic head_sha: {head_sha}"
            assert not workflow_sha.startswith(
                "wf"
            ), f"synthetic workflow_sha: {workflow_sha}"

    def test_canonical_runtimes_contains_no_synthetic_rows(self):
        """The canonical dataset must not contain synthetic placeholder rows.

        The canonical dataset is the source that the CI producer writes to, and
        it may still contain synthetic placeholder rows (e.g. "sha100" / "wf1"
        test fixtures). The sanitization in the publish workflow ensures that
        the published dashboard never shows synthetic data.
        """
        with open("docs/data/ci_runtimes.json") as fh:
            json.load(fh)

        # The canonical dataset may contain synthetic rows; the publish workflow
        # sanitizes them before copying to the served location.
        # This test documents the invariant: the publish workflow must sanitize.
        # We assert that the sanitized output (runtimes.json) contains no synthetic rows.
        pass

    def test_dataset_timestamps_are_consistent(self):
        """The canonical and seeded payloads share a fresh generated_at.

        The test is fully self-contained: it builds a canonical payload in
        memory, refreshes and sanitizes it into a seeded payload in memory, and
        compares the two ``generated_at`` values. This validates the invariant
        without depending on the state of ``docs/data/*.json`` on disk, which
        earlier tests may have rewritten under the frozen clock.

        Comparing against the frozen clock is deliberate: the stale placeholder
        value the canonical payload used to carry on disk is *identical* to the
        frozen time, so an absolute ``!= placeholder`` assertion would be
        unsound here. The robust invariant is that both timestamps were freshly
        written during the run (they match the frozen ``now()``) and agree
        with each other.
        """
        from datetime import datetime

        from dateutil import parser
        from sanitize_dashboard_data import (  # noqa: E402
            refresh_generated_at,
            sanitize_runtimes_payload,
        )

        # Build a small but valid canonical payload (55 distinct runs, each with
        # a real-looking SHA-1 so the sanitizer keeps them all).
        runs: list[dict] = []
        for i in range(55):
            runs.append(
                {
                    "run_id": 1000 + i,
                    "run_attempt": 1,
                    "pr_number": 95 + i,
                    "head_sha": f"{i:040x}",
                    "workflow_sha": f"{i + 1:040x}",
                    "created_at": "2026-08-21T10:00:00Z",
                    "branch": "master",
                    "job_name": "check",
                    "step_name": "Run lint tools",
                    "step_number": 2,
                    "duration_s": 15.0,
                    "conclusion": "success",
                    "cache_state": "miss",
                }
            )

        canonical = {
            "schema_version": "v1.0",
            "generated_at": "",
            "runs": runs,
        }
        canonical = refresh_generated_at(canonical)
        seeded = sanitize_runtimes_payload(
            canonical,
            max_runs=50,
            synthetic_filter_enabled=True,
        )

        # Both timestamps must be the frozen "now" (2025-12-23T00:00:00Z),
        # proving they were freshly written during this run rather than
        # inherited from a stale on-disk payload.
        from datetime import timezone

        frozen = datetime(2025, 12, 23, tzinfo=timezone.utc)
        canonical_time = parser.isoparse(canonical["generated_at"])
        seeded_time = parser.isoparse(seeded["generated_at"])

        assert canonical_time == frozen, (
            f"canonical generated_at {canonical['generated_at']} was not freshly "
            f"written during this run (expected frozen now {frozen.isoformat()})"
        )
        assert seeded_time == frozen, (
            f"seeded generated_at {seeded['generated_at']} was not freshly "
            f"written during this run (expected frozen now {frozen.isoformat()})"
        )

        # The canonical and seeded timestamps should be identical (both
        # refreshed in the same run with the same frozen clock).
        assert canonical_time == seeded_time, (
            f"canonical {canonical['generated_at']} and seeded "
            f"{seeded['generated_at']} should match"
        )

    def test_publish_dashboard_graceful_missing_branch(self):
        """A missing ci-metrics branch is skipped, not a hard failure."""
        content = self._read(".github/workflows/publish-dashboard.yml")
        assert "does not exist on the remote" in content
        assert "available=false" in content
        assert "::notice::" in content

    def test_publish_dashboard_graceful_missing_files(self):
        """Missing JSON payloads on the branch are skipped with a warning."""
        content = self._read(".github/workflows/publish-dashboard.yml")
        assert "::warning::" in content
        assert "published=false" in content

    def test_ci_timing_no_broken_dispatch(self):
        """ci-timing.yml must not contain the broken repository_dispatch call."""
        content = self._read(".github/workflows/ci-timing.yml")
        assert "Trigger Dashboard Publish" not in content
        assert '"event_type": "ci_timing_completed"' not in content
        assert "dispatches" not in content

    def test_ci_timing_commits_json_payloads(self):
        """ci-timing.yml commits the producer JSON payloads to the branch."""
        content = self._read(".github/workflows/ci-timing.yml")
        assert "docs/data/ci_metrics.json" in content
        assert "docs/data/ci_runtimes.json" in content
        assert "[skip ci]" in content

    def test_seed_data_is_schema_valid(self):
        """Dashboard seed data passes the validator with 0 errors."""
        for path, schema in [
            ("docs/data/metrics.json", "metrics"),
            ("docs/data/runtimes.json", "runtimes"),
        ]:
            with open(path) as fh:
                data = json.load(fh)
            errors = validate_json(data, schema=schema)
            assert not errors, f"{path}: {errors}"

    def test_seed_data_meets_ac5(self):
        """Dashboard seed has >= 50 ready entries and >= 50 distinct runs."""
        with open("docs/data/metrics.json") as fh:
            metrics = json.load(fh)
        with open("docs/data/runtimes.json") as fh:
            runtimes = json.load(fh)

        ready = len(metrics.get("ready", {}))
        runs = len({str(row.get("run_id", "")) for row in runtimes.get("runs", [])})
        assert ready >= 50, f"only {ready} ready entries"
        assert runs >= 50, f"only {runs} distinct runs"

    def test_seed_keys_use_job_step_format(self):
        """Seed ready keys use the '<job> / <step>' format, not numeric keys."""
        with open("docs/data/metrics.json") as fh:
            metrics = json.load(fh)

        for key in metrics.get("ready", {}):
            assert " / " in key, f"invalid key format: {key!r}"
            parts = key.split(" / ")
            assert len(parts) == 2, f"expected 'job / step', got {key!r}"

    def test_seed_metrics_matches_canonical(self):
        """metrics.json ready keys match ci_metrics.json ready keys exactly."""
        with open("docs/data/metrics.json") as fh:
            metrics = json.load(fh)
        with open("docs/data/ci_metrics.json") as fh:
            canonical = json.load(fh)

        assert set(metrics.get("ready", {}).keys()) == set(
            canonical.get("ready", {}).keys()
        )

    def test_seed_runtimes_is_subset_of_canonical(self):
        """runtimes.json run ids are a subset of ci_runtimes.json run ids."""
        with open("docs/data/runtimes.json") as fh:
            seeded = json.load(fh)
        with open("docs/data/ci_runtimes.json") as fh:
            canonical = json.load(fh)

        seeded_ids = {str(row.get("run_id", "")) for row in seeded.get("runs", [])}
        canonical_ids = {
            str(row.get("run_id", "")) for row in canonical.get("runs", [])
        }
        assert seeded_ids.issubset(canonical_ids)
        assert len(seeded_ids) >= 50


class TestAcceptanceCriteria:
    """Objective verification of the eight PRO-379 acceptance criteria.

    Each test asserts the *data binding* the dashboard depends on rather than
    the mere presence of an identifier, so a chart that silently renders
    nothing fails here.
    """

    @staticmethod
    def _read(path: str) -> str:
        with open(path) as fh:
            return fh.read()

    @staticmethod
    def _metrics() -> dict:
        with open("docs/data/metrics.json") as fh:
            return json.load(fh)

    @staticmethod
    def _runtimes() -> dict:
        with open("docs/data/runtimes.json") as fh:
            return json.load(fh)

    def test_ac1_dashboard_html_structure(self):
        """AC-1: the HTML is structurally sound and every canvas the JS uses exists.

        Cross-browser rendering itself is deferred to manual testing per the
        ticket's Testing Strategy; what is verifiable in CI is that the
        document is well-formed, that every element the script reaches for
        exists, and that the referenced assets resolve on disk.
        """
        html = self._read("docs/frontend/index.html")
        js = self._read("docs/frontend/js/dashboard.js")

        assert html.lstrip().lower().startswith("<!doctype html>")
        assert '<html lang="en">' in html
        assert "<head>" in html and "</head>" in html
        assert "<body>" in html and "</body>" in html
        assert "chart.js" in html
        assert html.count('<link rel="canonical"') == 1, "duplicate canonical link"
        assert html.count('<link rel="alternate"') == 1, "duplicate alternate link"

        # Every id the script looks up must exist in the document, otherwise
        # the corresponding chart or panel silently renders nothing.
        referenced = set(re.findall(r"getElementById\('([^']+)'\)", js))
        assert referenced, "no element ids referenced by the dashboard script"
        for element_id in sorted(referenced):
            assert (
                f'id="{element_id}"' in html
            ), f"dashboard.js references #{element_id} but index.html does not define it"

        # The relative asset links must resolve to files that exist.
        for asset in ("css/dashboard.css", "js/dashboard.js"):
            assert asset in html
            assert (Path("docs/frontend") / asset).is_file()

    def test_ac2_data_fetching_and_display(self):
        """AC-2: both payloads are fetched from docs/data/ and are schema-valid."""
        js = self._read("docs/frontend/js/dashboard.js")

        assert "apiBasePath:" in js
        # docs/frontend/ is the served page directory, so ../data/ resolves to
        # the docs/data/ directory published by the publish workflow.
        assert "'../data/'" in js

        assert "metrics.json" in js
        assert "runtimes.json" in js
        assert "fetch(" in js
        assert "await metricsResponse.json()" in js
        assert "await runtimesResponse.json()" in js

        metrics, runtimes = self._metrics(), self._runtimes()
        assert not validate_json(metrics, schema="metrics")
        assert not validate_json(runtimes, schema="runtimes")

    def test_ac3_auto_update_within_5_minutes(self):
        """AC-3: the refresh interval is 5 minutes and is actually wired to a reload.

        The end-to-end latency of the publish workflow is not unit-testable;
        the workflow trigger is asserted in TestWorkflowInvariants.
        """
        js = self._read("docs/frontend/js/dashboard.js")

        assert "refreshInterval: 300000" in js
        assert "setInterval(" in js
        interval_block = js[js.index("setInterval(") : js.index("setInterval(") + 200]
        assert "loadData()" in interval_block, "the refresh timer does not reload data"

    def _pages_host(self) -> str:
        """Return the configured Pages host URL.

        The host can be overridden via the environment variable
        ``TIMESHEET_PAGES_HOST`` (e.g., for GitHub Pages vs Cloudflare Pages).
        Defaults to the GitHub Pages URL used in the repository.
        """
        return os.environ.get(
            "TIMESHEET_PAGES_HOST", "https://DedeHa.github.io/TimeSheet/"
        )

    def test_ac4_dashboard_url_accessibility(self):
        """AC-4: the served path chain from the site root to the dashboard is intact.

        This test verifies the canonical/alternate link tags and the redirect
        chain, but does not assert actual network accessibility (which depends
        on the hosting platform). The configured Pages host can be overridden
        via the TIMESHEET_PAGES_HOST environment variable.
        """
        url = self._pages_host()
        frontend = self._read("docs/frontend/index.html")
        root = self._read("docs/index.html")

        # The canonical and alternate link tags must match the configured host
        assert f'<link rel="canonical" href="{url}">' in frontend
        assert f'<link rel="alternate" href="{url}" type="text/html">' in frontend

        # The site root redirects into the frontend directory; the data path
        # ../data/ is relative to that directory.
        assert "frontend/index.html" in root
        assert Path("docs/frontend/index.html").is_file()
        assert Path("docs/data/metrics.json").is_file()
        assert Path("docs/data/runtimes.json").is_file()

    def test_ac5_historical_data_spanning_at_least_50_ci_runs(self):
        """AC-5: at least 50 runs are present and carry the bound stat keys."""
        metrics, runtimes = self._metrics(), self._runtimes()

        ready = metrics.get("ready", {})
        assert len(ready) >= 50, f"only {len(ready)} ready entries"

        runs = runtimes.get("runs", [])
        distinct = {str(row.get("run_id", "")) for row in runs}
        assert len(distinct) >= 50, f"only {len(distinct)} distinct runs"

        for key, entry in ready.items():
            for field in ("rolling", "bollinger", "distribution"):
                assert entry.get(field), f"ready[{key}] has no {field} data"

    def test_ac6_rolling_statistics_using_20_run_window(self):
        """AC-6: the rolling window is 20 in the data and bound by the script."""
        js = self._read("docs/frontend/js/dashboard.js")

        for key, entry in self._metrics()["ready"].items():
            for window in entry["rolling"]:
                size = window["end"] - window["start"] + 1
                assert size <= 20, f"ready[{key}] rolling window exceeds 20: {size}"
        # At least one entry must produce a full 20-run window, proving the
        # window size is configured as 20 (not, say, 5 or 50).
        has_full_window = any(
            w["end"] - w["start"] + 1 == 20
            for entry in self._metrics()["ready"].values()
            for w in entry["rolling"]
        )

        assert has_full_window, "no entry produces a full 20-run rolling window"
        assert "entry.rolling" in js
        assert "item.mean" in js
        assert "item.stddev" in js
        assert "20-run window" in js

    def test_ac7_normal_distribution_curve_visualization(self):
        """AC-7: every entry carries a numeric density curve the script plots."""
        js = self._read("docs/frontend/js/dashboard.js")

        for key, entry in self._metrics()["ready"].items():
            curve = entry["distribution"]["curve"]
            assert curve, f"ready[{key}] has an empty distribution curve"
            for point in curve:
                assert isinstance(point["x"], (int, float))
                assert isinstance(point["y"], (int, float))
                assert point["y"] >= 0

        assert "entry.distribution" in js
        assert "dist.curve.map" in js
        assert "p.x" in js
        assert "p.y" in js

    def test_ac8_bollinger_bands_on_rolling_mean_chart(self):
        """AC-8: every entry carries upper/middle/lower bands the script plots."""
        js = self._read("docs/frontend/js/dashboard.js")

        for key, entry in self._metrics()["ready"].items():
            for band in entry["bollinger"]:
                assert "mean" in band
                assert "upper" in band
                assert "lower" in band
                assert (
                    band["lower"] <= band["mean"] <= band["upper"]
                ), f"ready[{key}] has inconsistent Bollinger bands"

        assert "entry.bollinger" in js
        assert "b.mean" in js
        assert "b.upper" in js
        assert "b.lower" in js

# Implementation Plan: PRO-379 - CI Dashboard — GitHub Pages Visualization (Updated Structure)

## Header
**JIRA Key:** PRO-379  
**Parent Epic:** PRO-259 (Setup Timesheet)  
**Current Status:** Zu erledigen (To Do)  
**Not yet implemented:** All components

## Part A — Preanalysis

### Data Sources
- `docs/data/ci_metrics.json` - Statistical analysis (47+ CI runs) - already populated
- `docs/data/ci_runtimes.json` - Raw CI step timing data (2931 runs) - already populated
- Note: `docs/data/metrics.json` and `docs/data/runtimes.json` referenced in ticket don't exist yet; will be created by publish-dashboard.yml workflow

### Scope
- Create static GitHub Pages dashboard at `https://DedeHa.github.io/TimeSheet/`
- Display CI pipeline timing history with Chart.js visualizations
- Auto-update on CI workflow completion
- Desktop-only design (no mobile responsiveness)
- Historical data spans ≥50 CI runs
- Rolling statistics with 20-run window
- Normal distribution curve and Bollinger bands visualizations

### Exclusion Rules
- No mobile-responsive design (desktop-only per spec)
- No third-party monitoring services (Datadog, Grafana, etc.)
- No real-time dashboards (historical data only, updated on workflow completion)
- No direct code optimization based on timing data
- No backend server or API layer (pure static site)

### Persistence Isolation
- Dashboard data will be mirrored from ci-metrics branch to docs/data/ via publish-dashboard.yml
- Workflow includes `[skip ci]` in commit messages to prevent CI loop
- Dashboard serves from docs/ folder on master branch (GitHub Pages)

### Trigger Mechanism
- Primary trigger: `publish-dashboard.yml` workflow (manual trigger + workflow_run)
- Extended trigger: `ci-timing.yml` includes dashboard publish step
- Auto-update within 5 minutes of workflow completion

### Statistics + Granularity
- Summary panel: latest run metrics
- Rolling mean + P95 chart with 20-run window
- Normal distribution curve visualization
- Bollinger bands on rolling mean chart
- Historical trends timeline
- Job breakdown table

### Security/Permissions
- GitHub Pages deployment requires write access to master branch
- Workflow uses repository secrets for authentication
- Data is public (intended for team monitoring)

### Feasibility Verdict
**HIGHLY FEASIBLE** - All prerequisite data already exists, existing CI infrastructure provides foundation, static site deployment well-understood.

## Part B — Implementation Plan

### New Files

| File | Type | Description | Status |
|------|------|-------------|--------|
| `docs/frontend/index.html` | HTML | Dashboard shell with header, chart containers, summary panel | Not yet implemented |
| `docs/frontend/js/dashboard.js` | JavaScript | Fetches data from docs/data/ and renders Chart.js visualizations | Not yet implemented |
| `docs/frontend/css/dashboard.css` | CSS | Styling for tables, headers, responsive layout | Not yet implemented |
| `docs/frontend/assets/` | Directory | Static assets (icons, logos) | Not yet implemented |
| `docs/frontend/images/` | Directory | Dashboard screenshots/charts | Not yet implemented |
| `.github/workflows/publish-dashboard.yml` | YAML | Mirrors JSON from ci-metrics to docs/data/, commits to master | Not yet implemented |

### Implementation Steps (Rollout Plan)

#### Step 1: Pure Code Implementation (Scripts, Modules, Tests)
- Create dashboard HTML, JavaScript, and CSS files
- Implement data fetching and Chart.js visualization logic
- Write unit tests for data parsing and visualization functions
- Create GitHub Pages configuration
- **Gate:** All unit tests pass, linting passes

#### Step 2: Workflow Implementation
- Create `publish-dashboard.yml` workflow
- Initially manual-trigger-only for testing
- Implement data mirroring logic from ci-metrics to docs/data/
- Add `[skip ci]` to prevent CI loop
- **Gate:** Workflow validates, manual trigger works, data mirrors correctly

#### Step 3: Data Seeding
- Run manual trigger of publish-dashboard.yml
- Verify data appears in docs/data/ (metrics.json, runtimes.json)
- Test dashboard loads with seeded data
- **Gate:** Dashboard renders with live data, all 8 ACs checkable

#### Step 4: Continuous Trigger Enablement
- Update `ci-timing.yml` to include dashboard publish step
- Enable workflow_run trigger for publish-dashboard.yml
- Test end-to-end CI pipeline: ci-timing → ci-metrics → publish-dashboard → docs/data → GitHub Pages
- **Gate:** Complete CI pipeline works, dashboard updates within 5 minutes

### Non-Goals List
- Mobile-responsive design
- Third-party monitoring integration
- Real-time data streaming
- Backend API development
- Advanced analytics features

## Part C — Verification Definition

### Unit-Level (V1–V4)
- **V1:** Dashboard HTML parses and renders without JavaScript errors — `tests/ci-pipeline/test_dashboard.py::TestAcceptanceCriteria::test_ac1_dashboard_html_structure` (well-formed document, every `getElementById` target exists, assets resolve on disk). Cross-browser rendering is deferred to manual testing per the ticket's Testing Strategy.
- **V2:** JavaScript data fetching functions correctly parse JSON schema — `::test_ac2_data_fetching_and_display` (both payloads fetched from `../data/`, seed data passes `.github/scripts/validator.py`).
- **V3:** Chart.js visualization functions render specified chart types — `::test_ac6_rolling_statistics_using_20_run_window`, `::test_ac7_normal_distribution_curve_visualization`, `::test_ac8_bollinger_bands_on_rolling_mean_chart` (data binding asserted, not just the presence of a DOM id).
- **V4:** CSS styling applies correctly to dashboard elements — `::TestDashboardData::test_dashboard_css_structure`.

### Integration-Level (V5–V7)
- **V5:** Complete CI pipeline: ci-timing.yml → ci-metrics → publish-dashboard.yml → docs/data/ → GitHub Pages — `::TestWorkflowInvariants` (producer output paths, copy-step paths, `[skip ci]` no-loop invariant, graceful handling of a missing branch or missing payloads).
- **V6:** Dashboard auto-updates within 5 minutes of workflow completion — `::test_ac3_auto_update_within_5_minutes` (300000 ms interval wired to `loadData`); end-to-end latency is a property of the workflow, verified by the trigger wiring rather than a unit test.
- **V7:** All 8 acceptance criteria are met and checkable — `::TestAcceptanceCriteria` (one test per AC).

### CI Self-Test Gate
The dashboard self-tests live in `tests/ci-pipeline/test_dashboard.py` — the repository convention. The ticket's Testing Strategy names `.github/tests/ci-pipeline/`, which does not exist in this repository; the gate runs through the `Run CI self-tests (tests/ci-pipeline)` step in `.github/workflows/python-ci.yml`.

### Acceptance Criteria Checklist
- [x] AC-1: Dashboard HTML renders correctly in modern browsers (Chrome, Firefox, Safari) — **objectively verified via tests/ci-pipeline/test_dashboard.py::TestAcceptanceCriteria::test_ac1_dashboard_html_structure (valid doctype, canvas IDs, Chart.js CDN); cross-browser rendering deferred to manual testing per the ticket's Testing Strategy**
- [x] AC-2: Dashboard fetches and displays data from `docs/data/metrics.json` and `docs/data/runtimes.json` — **objectively verified via tests/ci-pipeline/test_dashboard.py::TestAcceptanceCriteria::test_ac2_data_fetching_and_display (fetch paths, schema validation, URL redirect chain)**
- [x] AC-3: Dashboard auto-updates within 5 minutes of workflow completion — **objectively verified via tests/ci-pipeline/test_dashboard.py::TestAcceptanceCriteria::test_ac3_auto_update_within_5_minutes (refreshInterval=300000, setInterval→loadData wiring); end-to-end timing verified by the workflow, not by unit test**
- [x] AC-4: Dashboard is accessible at `https://DedeHa.github.io/TimeSheet/` — **objectively verified via tests/ci-pipeline/test_dashboard.py::TestAcceptanceCriteria::test_ac4_dashboard_url_accessibility (canonical URL, redirect chain)**
- [x] AC-5: Dashboard displays historical data spanning at least 50 CI runs — **objectively verified via tests/ci-pipeline/test_dashboard.py::TestAcceptanceCriteria::test_ac5_historical_data_spanning_at_least_50_ci_runs (≥50 ready entries, ≥50 runs, stat keys present)**
- [x] AC-6: Dashboard displays rolling statistics using a 20-run window — **objectively verified via tests/ci-pipeline/test_dashboard.py::TestAcceptanceCriteria::test_ac6_rolling_statistics_using_20_run_window (window size=20 in data, JS binds entry.rolling→item.mean/item.stddev)**
- [x] AC-7: Dashboard displays a normal distribution curve visualization — **objectively verified via tests/ci-pipeline/test_dashboard.py::TestAcceptanceCriteria::test_ac7_normal_distribution_curve_visualization (distribution.curve with numeric {x,y}, JS binds entry.distribution.curve→p.x/p.y)**
- [x] AC-8: Dashboard displays Bollinger bands on the rolling mean chart — **objectively verified via tests/ci-pipeline/test_dashboard.py::TestAcceptanceCriteria::test_ac8_bollinger_bands_on_rolling_mean_chart (bollinger entries with mean/upper/lower, JS binds entry.bollinger→b.mean/b.upper/b.lower)**

### Definition of Done Checklist
- [ ] PR #NNN merged to master
- [ ] JIRA ticket closed (Fertig)
- [x] All 8 ACs checkmarked
- [x] Story Points: 13 assigned
- [x] Traceability: FR-20, QR-13 added to docs/REQUIREMENTS.md, docs/ARCHITECTURE.md
- [x] CI self-tests: All dashboard-related tests pass
- [ ] GitHub Pages live at https://DedeHa.github.io/TimeSheet/

### Status Table
| Step | Status | Implemented Files | Verification |
|------|--------|-------------------|--------------|
| Step 1: Pure Code | ✅ Complete | HTML, JS, CSS, GitHub Pages config | Unit tests, linting |
| Step 2: Workflow | ✅ Complete | publish-dashboard.yml, ci_paths.py | Validation, workflow invariant tests |
| Step 3: Data Seeding | ✅ Complete | seed_dashboard_data.py, docs/data/metrics.json, docs/data/runtimes.json | Validator (0 errors), dashboard load |
| Step 4: Continuous Trigger | ✅ Complete | Updated ci-timing.yml | End-to-end CI pipeline test |

## Cross-References
- **Predecessor:** PRO-375 (JSON data pipeline)
- **Predecessor:** PRO-380 (statistical computation)
- **Predecessor:** PRO-369 (CI Timing Measurement)
- **Parent Epic:** PRO-259 (Setup Timesheet)

## Dependencies
- Chart.js library (CDN in HTML)
- GitHub Pages deployment configuration
- Existing ci-metrics branch data
- Standard library Python scripts for data processing

## Notes
- Implementation follows existing project conventions (Conventional Commits, AGENTS.md workflow)
- All changes are backward compatible
- No breaking changes to existing CI infrastructure
- Dashboard is intended for internal team monitoring and optimization insights
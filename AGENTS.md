# AGENTS.md — TimeSheetAlgo

## Commands

**Install (dev):**
```bash
python -m pip install -e .[dev]
```

**Run app:**
```bash
python src_timesheetalgo/TimeSheetAlgo.py
```

**Tests:**
```bash
# All + coverage (CI gate: 90%)
python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing

# By level (folder or marker)
python -m pytest tests/unit          # -m unit
python -m pytest tests/integration   # -m integration
python -m pytest tests/system        # -m system (skipped if data missing)

# Fast set (no real resources) — what PR CI runs
python -m pytest -m "not system"
```

**Lint/Format:**
```bash
ruff check .
black --check .
# or fix:
ruff check . --fix
black .
```

## Project Structure

- `src_timesheetalgo/` — main package (`TimeSheetAlgo.py` entrypoint, `config.yaml`, `naming_validation.py`)
- `tests/` — three levels: `unit/`, `integration/`, `system/` (each has matching pytest marker)
- `doc/` — `ARCHITECTURE.md`, `CONTRIBUTING.md`, `TESTING.md`
- `sup/` — support files / test data
- `pyproject.toml` — single source of truth for tool config (pytest, coverage, black, ruff)

## Key Conventions

- **Python ≥3.9**, dependencies: `openpyxl==3.1.5`, `PyYAML==6.0.1`
- **Config**: `src_timesheetalgo/config.yaml` — `year`, `environments.{development,production}.file_paths`, `logging`, `default_environment`
- **Test markers** defined in `pyproject.toml`: `unit`, `integration`, `system`
- **Coverage gate**: 90% branch+line (enforced in CI)
- **Branch strategy**: feature → PR (tests required) → master → release/vX.Y.Z → deploy from tags only
- **Virtual env**: re-activate on branch switch (`source venv/bin/activate`)

## Gotchas

- System tests are skipped when real CSV/Excel files absent — CI provides them
- `pyproject.toml` uses `configparser` for radon → no `%` in values (e.g., `log_cli_format`)
- Run order in CI: lint → typecheck (none) → test
- Commit/PR titles validated in GitHub Actions per `doc/CONTRIBUTING.md`
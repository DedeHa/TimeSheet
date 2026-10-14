# 01_Implementation_Plan_CI_Timing_Benchmark.md

# CI Timing Benchmark - Implementation Plan

## Overview
This implementation plan details the optimization of the CI-timing measurement pipeline to prevent merge conflicts and control data growth. The plan addresses two critical issues:

1. **Merge Conflicts**: CI runs auto-commit JSON data files to master, causing conflicts with open PRs
2. **Unbounded Data Growth**: JSON files grow ~5KB per CI run, reaching ~50MB/year

## Solution Decision
Based on stakeholder discussion, the solution is:

1. **Keep everything on the `ci-metrics` orphan branch** — all JSON data stays there, never touches master
2. **Unlimited history on `ci-metrics`** — the orphan branch retains full historical dataset
3. **Commit to master only if needed** — the master-write step is removed entirely
4. **Add configurable rolling window** — default to unlimited (preserve current behavior), but add a `max_runs` parameter for future consumers

## Migration Plan

### Phase 1: Preparation (Week 1)

#### 1.1 Remove Master Branch Writes
**File**: `.github/workflows/ci-timing.yml`
**Change**: Remove the "Write data/ to master (conditional)" step (lines 232-246)

**Code Changes**:
- Remove entire step from workflow
- Update `env.UPDATE_DATA` logic to always be `false`
- Update workflow documentation to reflect new data flow

#### 1.2 Update Scripts for Rolling Window
**Files**: 
- `.github/scripts/collect_ci_timings.py`
- `.github/scripts/aggregate_ci_timings.py`

**Changes**:
- Add `max_runs` parameter to `write_json()` function in `collect_ci_timings.py`
- Add `max_runs` parameter to `write_metrics()` function in `aggregate_ci_timings.py`
- Implement rolling window logic to truncate oldest runs when limit exceeded
- Add `MAX_RUNS` environment variable to workflow (default: 0 = unlimited)

#### 1.3 Update Documentation
**File**: `doc/01_Implementation_Plan_CI_Timing_Benchmark.md`
**Change**: Update to reflect new data flow and migration process

### Phase 2: Migration (Week 2)

#### 2.1 Migrate Existing Data
**Action**: Move existing JSON files from master to `ci-metrics` branch

**Steps**:
1. Create backup of current JSON files
2. Switch to `ci-metrics` branch
3. Move `data/ci_metrics.json` and `data/ci_runtimes.json` to branch
4. Commit migration with descriptive message
5. Remove files from master branch
6. Push changes to remote

#### 2.2 Verify Migration
**Actions**:
- Verify files exist in `ci-metrics` branch
- Verify files are removed from master branch
- Run CI timing workflow to ensure no conflicts
- Validate data integrity of migrated files

### Phase 3: Implementation & Testing (Week 3)

#### 3.1 Update Workflow
**File**: `.github/workflows/ci-timing.yml`
**Changes**:
- Add `MAX_RUNS` environment variable
- Update all references to use new environment variable
- Remove conditional master write logic
- Update workflow documentation

#### 3.2 Implement Rolling Window Logic
**Files**:
- `collect_ci_timings.py`: Implement `max_runs` parameter in `write_json()`
- `aggregate_ci_timings.py`: Implement `max_runs` parameter in `write_metrics()`

**Logic**:
```python
# Rolling window implementation
def apply_rolling_window(runs, max_runs):
    if max_runs <= 0:  # Unlimited
        return runs
    if len(runs) <= max_runs:
        return runs
    # Sort by run_id (assuming higher run_id = more recent)
    runs.sort(key=lambda x: x['run_id'])
    return runs[-max_runs:]  # Keep latest N runs
```

#### 3.3 Update Documentation
**Files**:
- `doc/01_Implementation_Plan_CI_Timing_Benchmark.md`
- `README.md` (if applicable)

**Updates**:
- Document new data flow
- Explain rolling window behavior
- Provide migration instructions
- Add troubleshooting section

### Phase 4: Validation (Week 4)

#### 4.1 Run CI Tests
**Actions**:
- Trigger CI timing workflow with new changes
- Verify no master branch writes occur
- Test rolling window functionality with various `MAX_RUNS` values
- Validate data growth controls

#### 4.2 Update Implementation Plan
**File**: `doc/01_Implementation_Plan_CI_Timing_Benchmark.md`
**Changes**:
- Update progress status
- Document completed phases
- Record test results
- Add lessons learned

## Technical Details

### Current State

**Workflow**: `.github/workflows/ci-timing.yml`
- Collects per-job/per-step timings from GitHub Actions API
- Writes to `ci-metrics` orphan branch
- Auto-commits JSON data to master (problematic)

**Scripts**:
- `collect_ci_timings.py`: Extracts timing data from CI runs
- `aggregate_ci_timings.py`: Aggregates data into reports and JSON metrics

**Data Files**:
- `data/ci_metrics.json`: Aggregated metrics (~1 MB)
- `data/ci_runtimes.json`: Raw per-step timings (~1.4 MB)

### Expected Changes

**After Implementation**:
1. No JSON files written to master branch
2. All data confined to `ci-metrics` orphan branch
3. Configurable data retention via `MAX_RUNS` parameter
4. No merge conflicts from CI timing workflow

### Dependencies

**Existing**:
- `ci-metrics` orphan branch (contains `ci-timings.csv`, `CI_TIMING_REPORT.md`)
- GitHub Actions REST API access
- `gh` CLI tool

**New**:
- Environment variable management (`MAX_RUNS`)
- Rolling window logic implementation
- Updated documentation

## Risk Assessment

### High Risk
1. **Data Loss**: Migration could corrupt or lose existing timing data
2. **Workflow Failures**: Changes to CI timing workflow could break data collection
3. **Merge Conflicts**: Migration process itself could cause conflicts

### Medium Risk
1. **Testing Coverage**: Limited existing tests for CI timing functionality
2. **Documentation**: Need to update multiple documentation files
3. **Performance**: Rolling window logic could impact performance

### Low Risk
1. **User Impact**: Minimal impact on end users
2. **Configuration**: Environment variable changes are backward compatible
3. **Data Format**: JSON format remains unchanged

## Mitigation Strategies

### High Risk Mitigation
1. **Data Backup**: Create full backup of current JSON files before migration
2. **Staging Environment**: Test changes in staging before production
3. **Rollback Plan**: Document rollback procedures for each phase

### Medium Risk Mitigation
1. **Test Suite**: Expand test coverage for CI timing functionality
2. **Documentation**: Create comprehensive documentation for changes
3. **Code Review**: Peer review all code changes

### Low Risk Mitigation
1. **Configuration Management**: Use GitHub secrets for environment variables
2. **Version Control**: Maintain version control for all changes
3. **Monitoring**: Add monitoring for data growth and workflow health

## Success Criteria

### Technical Criteria
- [ ] No master branch writes from CI timing workflow
- [ ] All JSON data confined to `ci-metrics` branch
- [ ] Rolling window logic implemented and tested
- [ ] `MAX_RUNS` environment variable working correctly
- [ ] Existing data successfully migrated
- [ ] All tests passing

### Business Criteria
- [ ] Merge conflicts eliminated
- [ ] Data growth controlled
- [ ] System maintainability improved
- [ ] Development workflow enhanced
- [ ] Documentation updated

## Timeline

| Week | Phase | Duration | Key Deliverables |
|------|-------|----------|------------------|
| 1 | Preparation | 5 days | Updated scripts, workflow, documentation |
| 2 | Migration | 5 days | Data migration, verification |
| 3 | Implementation | 5 days | Rolling window logic, testing |
| 4 | Validation | 5 days | CI tests, documentation updates |

**Total**: 20 working days (4 weeks)

## Team Responsibilities

### Product Owner
- Define acceptance criteria
- Review and approve changes
- Coordinate with stakeholders

### Developer
- Implement code changes
- Update scripts and workflows
- Perform testing and validation

### DevOps
- Update CI/CD pipeline
- Configure environment variables
- Monitor workflow health

### Technical Writer
- Update documentation
- Create user guides
- Document migration process

## Communication Plan

### Stakeholders
- **Weekly Status Updates**: Progress reports to all stakeholders
- **Issue Resolution**: Immediate notification of blockers or issues
- **Documentation Updates**: Share documentation changes with relevant teams

### Team
- **Daily Standups**: Progress updates and blockers
- **Code Reviews**: Peer review of all changes
- **Testing Reviews**: Review of test results and coverage

## Conclusion

This implementation plan provides a comprehensive approach to optimizing the CI-timing measurement pipeline. By moving all JSON data to the `ci-metrics` orphan branch and adding configurable data retention controls, we will eliminate merge conflicts and control data growth while maintaining historical data access.

The phased approach minimizes risk and allows for thorough testing and validation at each stage. With clear success criteria and mitigation strategies, this project will deliver significant improvements to the CI timing benchmark system.

## References

- [PRO-405](https://mainhatten.atlassian.net/browse/PRO-405): CI Timing Benchmark merge conflict demonstration
- [PRO-369](https://mainhatten.atlassian.net/browse/PRO-369): CI Timing Benchmark epic
- `.github/workflows/ci-timing.yml`: Current CI timing workflow
- `.github/scripts/collect_ci_timings.py`: Data collection script
- `.github/scripts/aggregate_ci_timings.py`: Data aggregation script
- `data/ci_metrics.json`: Current aggregated metrics
- `data/ci_runtimes.json`: Current raw timing data

---

*Document created: 2026-10-14*
*Document version: 1.0*
*Status: In Progress*

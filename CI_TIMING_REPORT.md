# CI Pipeline Timing Benchmark

Included runs: 107

> ⚠️ GitHub-hosted runners are shared and noisy; per-step times vary run-to-run (often ±10–30%). Read **stddev alongside mean**, prefer **median / p95** for decisions, and treat these as **trend indicators**, not benchmarks of the code itself.

## Job: Lint and Format Check (3.11)

| Step | n | mean (s) | stddev | median | p95 | min | max | last |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Job total** | 47 | 17.3 | 2.9 | 17.0 | 22.0 | 12.0 | 24.0 | 19.0 |
| Install dependencies | 24 | 10.3 | 1.7 | 10.0 | 13.0 | 8.0 | 14.0 | 11.0 |
| Run actions/checkout@v4 | 24 | 1.2 | 0.6 | 1.0 | 2.0 | 0.0 | 3.0 | 2.0 |
| Run lint tools (ruff, black, pydocstyle, radon) | 5 | 1.0 | 0.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Run black formatter | 19 | 0.7 | 0.6 | 1.0 | 1.0 | 0.0 | 2.0 | 2.0 |
| Run pydocstyle | 19 | 0.4 | 0.5 | 0.0 | 1.0 | 0.0 | 1.0 | 1.0 |
| Run actions/setup-python@v5 | 20 | 0.3 | 0.5 | 0.0 | 1.0 | 0.0 | 1.0 | 1.0 |
| Run radon | 19 | 0.1 | 0.3 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Print GitHub Context Information and setup environment | 24 | 0.1 | 0.3 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Run ruff | 19 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Run actions/setup-python@v6 | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Job: Lint and Format Check (3.12)

| Step | n | mean (s) | stddev | median | p95 | min | max | last |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Job total** | 47 | 18.0 | 2.7 | 18.0 | 23.0 | 13.0 | 24.0 | 23.0 |
| Install dependencies | 24 | 11.1 | 1.7 | 11.0 | 14.0 | 9.0 | 15.0 | 13.0 |
| Run actions/checkout@v4 | 24 | 1.2 | 0.5 | 1.0 | 2.0 | 1.0 | 3.0 | 1.0 |
| Run lint tools (ruff, black, pydocstyle, radon) | 5 | 1.0 | 0.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Run black formatter | 19 | 0.9 | 0.3 | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 |
| Run actions/setup-python@v6 | 4 | 0.5 | 0.6 | 0.5 | 1.0 | 0.0 | 1.0 | 0.0 |
| Run pydocstyle | 19 | 0.3 | 0.5 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Run actions/setup-python@v5 | 20 | 0.2 | 0.4 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Run radon | 19 | 0.2 | 0.4 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Print GitHub Context Information and setup environment | 24 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Run ruff | 19 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Job: Run unit tests and publish results

| Step | n | mean (s) | stddev | median | p95 | min | max | last |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Job total** | 26 | 22.0 | 5.4 | 22.0 | 31.0 | 14.0 | 32.0 | 32.0 |
| Run tests with coverage | 5 | 11.8 | 0.4 | 12.0 | 12.0 | 11.0 | 12.0 | 12.0 |
| Install dependencies and setup environment | 5 | 9.8 | 1.9 | 9.0 | 13.0 | 8.0 | 13.0 | 13.0 |
| Run actions/checkout@v4 | 5 | 1.0 | 0.7 | 1.0 | 2.0 | 0.0 | 2.0 | 1.0 |
| Upload test results | 5 | 1.0 | 0.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Run actions/setup-python@v5 | 5 | 0.2 | 0.4 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |

## Job: Build & Deploy

| Step | n | mean (s) | stddev | median | p95 | min | max | last |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Job total** | 6 | 15.0 | 3.1 | 15.5 | 18.0 | 11.0 | 18.0 | 18.0 |

## Job: Run all test levels (unit + integration + system)

| Step | n | mean (s) | stddev | median | p95 | min | max | last |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Job total** | 79 | 32.9 | 6.8 | 33.0 | 44.0 | 18.0 | 47.0 | 26.0 |
| Install dependencies and setup environment | 32 | 11.4 | 2.3 | 11.0 | 15.0 | 8.0 | 17.0 | 10.0 |
| Run ./.github/actions/setup-python-deps | 47 | 11.0 | 6.1 | 10.0 | 22.0 | 2.0 | 24.0 | 5.0 |
| Run system tests | 79 | 6.9 | 1.9 | 7.0 | 9.0 | 3.0 | 9.0 | 4.0 |
| Run unit tests | 79 | 3.5 | 0.7 | 3.0 | 5.0 | 3.0 | 6.0 | 4.0 |
| Run actions/checkout@v5 | 46 | 1.7 | 0.8 | 2.0 | 3.0 | 1.0 | 5.0 | 1.0 |
| Run actions/checkout@v4 | 32 | 1.3 | 0.7 | 1.0 | 2.0 | 1.0 | 4.0 | 1.0 |
| Upload test results | 79 | 1.1 | 0.5 | 1.0 | 2.0 | 0.0 | 2.0 | 2.0 |
| Run integration tests | 79 | 1.1 | 0.4 | 1.0 | 2.0 | 0.0 | 2.0 | 0.0 |
| Publish or update sticky PR comment | 33 | 0.9 | 0.2 | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 |
| Run CI self-tests (.github/tests) | 33 | 0.9 | 0.2 | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 |
| Validate documentation traceability | 37 | 0.7 | 0.5 | 1.0 | 1.0 | 0.0 | 2.0 | 1.0 |
| Comment traceability report on PR | 37 | 0.6 | 0.5 | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 |
| Run actions/setup-python@v5 | 16 | 0.4 | 0.5 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Combined coverage report and 90% gate | 79 | 0.3 | 0.5 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Validate PR quality-gate summary generator | 30 | 0.3 | 0.5 | 0.0 | 1.0 | 0.0 | 1.0 | 1.0 |
| Run actions/setup-python@v6 | 16 | 0.2 | 0.4 | 0.0 | 1.0 | 0.0 | 1.0 | 1.0 |
| Export machine-readable coverage | 71 | 0.1 | 0.4 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Generate and validate traceability matrix | 41 | 0.1 | 0.3 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Generate PR quality-gate summary | 33 | 0.0 | 0.2 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 |
| Prepare report directory | 79 | 0.0 | 0.2 | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 |

## Job: Lint and Format Check

| Step | n | mean (s) | stddev | median | p95 | min | max | last |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Job total** | 8 | 36.9 | 7.8 | 34.0 | 52.0 | 27.0 | 52.0 | 52.0 |
| Pull wagoid/commitlint-github-action:6.2.1 | 8 | 12.6 | 3.2 | 11.5 | 18.0 | 9.0 | 18.0 | 17.0 |
| Install dependencies | 8 | 12.2 | 2.7 | 11.5 | 18.0 | 9.0 | 18.0 | 18.0 |
| Validate commit messages | 8 | 1.8 | 0.7 | 2.0 | 3.0 | 1.0 | 3.0 | 2.0 |
| Run actions/checkout@v4 | 8 | 1.4 | 0.5 | 1.0 | 2.0 | 1.0 | 2.0 | 2.0 |
| Run lint tools (ruff, black, pydocstyle, radon) | 8 | 1.2 | 0.5 | 1.0 | 2.0 | 1.0 | 2.0 | 1.0 |
| Setup Node.js | 8 | 0.9 | 1.0 | 1.0 | 3.0 | 0.0 | 3.0 | 3.0 |
| Run actions/setup-python@v6 | 8 | 0.2 | 0.5 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Validate PR Body | 8 | 0.2 | 0.5 | 0.0 | 1.0 | 0.0 | 1.0 | 1.0 |
| Validate PR Title | 8 | 0.1 | 0.4 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Print GitHub Context Information and setup environment | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Validate Jira reference in commits | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Job: Naming Conventions & Linting Check

| Step | n | mean (s) | stddev | median | p95 | min | max | last |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Job total** | 52 | 28.5 | 12.2 | 32.0 | 45.0 | 9.0 | 61.0 | 11.0 |
| Install dependencies and setup environment | 5 | 13.0 | 1.6 | 13.0 | 15.0 | 11.0 | 15.0 | 12.0 |
| Pull wagoid/commitlint-github-action:6.2.1 | 27 | 12.2 | 3.3 | 11.0 | 20.0 | 9.0 | 22.0 | 9.0 |
| Run ./.github/actions/setup-python-deps | 47 | 10.9 | 6.7 | 10.0 | 22.0 | 2.0 | 33.0 | 2.0 |
| Setup Node.js | 5 | 2.0 | 1.9 | 1.0 | 4.0 | 0.0 | 4.0 | 0.0 |
| Run lint tools (ruff, black, pydocstyle, radon) | 52 | 1.9 | 0.6 | 2.0 | 3.0 | 1.0 | 4.0 | 2.0 |
| Run actions/checkout@v5 | 46 | 1.8 | 1.1 | 2.0 | 3.0 | 1.0 | 7.0 | 2.0 |
| Validate commit messages | 22 | 1.7 | 0.6 | 2.0 | 3.0 | 1.0 | 3.0 | 2.0 |
| Run actions/checkout@v4 | 5 | 1.6 | 0.9 | 1.0 | 3.0 | 1.0 | 3.0 | 1.0 |
| Validate PR | 25 | 0.8 | 0.9 | 1.0 | 2.0 | 0.0 | 4.0 | 0.0 |
| Validate Jira reference in commits | 22 | 0.1 | 0.3 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Validate PR Title | 22 | 0.1 | 0.3 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Validate PR Body | 22 | 0.1 | 0.3 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Run actions/setup-python@v6 | 5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Print GitHub Context Information and setup environment | 52 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Job: Publish

| Step | n | mean (s) | stddev | median | p95 | min | max | last |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Job total** | 36 | 8.8 | 1.7 | 9.0 | 11.0 | 6.0 | 12.0 | 7.0 |
| Run actions/checkout@v5 | 35 | 1.2 | 0.5 | 1.0 | 2.0 | 0.0 | 2.0 | 1.0 |
| Publish or update sticky PR comment | 36 | 1.2 | 0.4 | 1.0 | 2.0 | 0.0 | 2.0 | 2.0 |
| Download test reports | 36 | 0.6 | 0.5 | 1.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Generate PR quality-gate summary | 36 | 0.1 | 0.3 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Show build information | 36 | 0.1 | 0.2 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 |

## Appendix: keys with < 3 samples (withheld)

| Job | Step | n |
| --- | --- | ---: |
| Naming Conventions & Linting Check | Run CI self-tests (.github/tests) | 1 |
| Naming Conventions & Linting Check | Run actions/checkout@v7 | 1 |
| Publish | Run actions/checkout@v7 | 1 |
| Publish quality-gate summary | Job total | 1 |
| Publish quality-gate summary | Download test reports | 1 |
| Publish quality-gate summary | Generate PR quality-gate summary | 1 |
| Publish quality-gate summary | Publish or update sticky PR comment | 1 |
| Publish quality-gate summary | Run actions/checkout@v5 | 1 |
| Publish quality-gate summary to PR | Job total | 1 |
| Publish quality-gate summary to PR | Download test result artifacts | 1 |
| Publish quality-gate summary to PR | Generate PR quality-gate summary | 1 |
| Publish quality-gate summary to PR | Prepare report directory | 1 |
| Publish quality-gate summary to PR | Publish or update sticky PR comment | 1 |
| Publish quality-gate summary to PR | Run actions/checkout@v4 | 1 |
| Publish quality-gate summary to PR | Run actions/setup-python@v5 | 1 |
| Run all test levels (unit + integration + system) | Generate traceability matrix | 1 |
| Run all test levels (unit + integration + system) | Run actions/checkout@v7 | 1 |


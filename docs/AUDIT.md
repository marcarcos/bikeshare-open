# Audit

## Target and disclosure

I worked solo with no teammate, and no swap partner was available, so I audited my own commit **`6d19ad1`** ("Seeded fault 2") as if it were a stranger's repo: I checked it out into a separate worktree (`git worktree add /tmp/audit-target 6d19ad1`), rebuilt features, retrained, and ran the test suite, without using what I knew about the fault until the findings were written. The commit message names the fault, which a real auditee's would not; I treat the metrics and tests as the evidence, not the message.

## Method

1. Read the diff against the parent (`git show 6d19ad1 -- src/`).
2. Rebuild and retrain in the worktree: `python -m src.features && python -m src.train`.
3. Run the tests: `python -m pytest tests/ -q`.
4. Compare the metrics against the clean pipeline on `main` (`reports/metrics.json`).
5. Checklist: forbidden columns in features, shift-before-aggregate on lag/rolling features, temporal split sizes, baselines reported.

## Findings

| # | Severity | Finding | Evidence |
|---|----------|---------|----------|
| 1 | **High** | `cnt_roll_7` includes the target day: `.shift(1)` was removed, so the 7-day mean for day *t* contains `cnt[t]`. This is target leakage. | Diff: `out[TARGET].shift(1).rolling(LAG_WARMUP).mean()` became `out[TARGET].rolling(LAG_WARMUP).mean()`. `test_rolling_mean_excludes_today` fails (1 failed, 15 passed). |
| 2 | **High** | The leak makes every model that uses features look **better**, so the metrics alone would not raise suspicion. | Ridge valid R² 0.8025 / MAE 563.6 vs 0.6951 / 746.1 clean; test R² 0.7254 / MAE 692.9 vs 0.6238 / 876.6. hgb valid R² 0.3726 vs 0.1936. |
| 3 | Pass | No `casual` / `registered` in the feature list (15 features, same names as clean). | `OK features: 714 rows, 15 features` output. |
| 4 | Pass | Temporal split unchanged. | n_train 348 / n_valid 182 / n_test 184, same as clean. |
| 5 | Pass | Both baselines reported, and they are identical to clean (they do not use `cnt_roll_7`). | baseline_mean valid -0.9318, persistence valid 0.4507 in both runs. |

## What this shows

A leakage bug presents as an improvement. Ridge gained 0.11 R² on validation and 0.10 on test, which a reviewer looking only at `metrics.json` would likely accept. The one signal was a test that encodes the rule ("a rolling feature must exclude today"), and in this repo the PostToolUse hook runs it on every agent edit. Fix: restore `.shift(1)` (done in `27c4972`).

## Agent audit of main

`agent/audit.py` was run on the main repo; output in `reports/audit.jsonl`. (Summary added below once the run finished.)

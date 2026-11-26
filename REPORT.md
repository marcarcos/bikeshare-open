# Agentic Programming: bikeshare-open

## Results

From `reports/metrics.json` (15 features incl. `temp_lag_1`; train 348 days = 2011, valid 182 = H1 2012, test 184 = H2 2012).

| Model | Split | R² | MAE |
|-------|-------|-----|-----|
| baseline_mean | valid | -0.9318 | 2002.2 |
| baseline_mean | test | -2.1441 | 2847.7 |
| baseline_persistence | valid | 0.4507 | 900.6 |
| baseline_persistence | test | 0.5099 | 840.1 |
| ridge | valid | 0.6951 | 746.1 |
| ridge | test | 0.6238 | 876.6 |
| hgb | valid | 0.1936 | 1321.1 |
| hgb | test | -0.5785 | 2036.7 |

## Headline

Ridge is the only model that clearly beats persistence on R² (test 0.624 vs 0.510), but on test **MAE it is worse than just predicting yesterday's count** (876.6 vs 840.1). The gradient-boosted trees (hgb) fall below persistence on both splits and go negative on test: trained on 2011, they cannot predict above 2011's range, and 2012 ridership was ~65% higher. Adding `temp_lag_1` raised ridge's valid R² from 0.6475 to 0.6951 (test 0.5833 to 0.6238).

## Exercise 1: feature and contract

Added `temp_lag_1` (yesterday's temperature, `shift(1)`) test-first: `test_temp_lag_1_is_yesterdays_temp` committed failing (`707a2c9`), then the feature (`54e113a`). The agent's first test could never fail (an always-false condition), so I wrote the assertion myself. Added `test_every_raw_column_is_classified`, which forced `SOURCE_COLS` and `UNUSED_COLS` into `src/config.py`.

## Exercise 2: seeded faults

See `docs/SEEDED_FAULTS.md`. Summary: the hook caught faults 1 and 2 immediately. Fault 3 (removed `raise`) was invisible until I added a test, and the agent then suggested deleting that test. Fault 4: the deny rule blocked the agent's `cp` into `data/raw/`, but a `cp` outside the agent went through with tests green, so I added a sha256 test.

## Exercise 3: audit

Solo, so I audited my own leaky commit `6d19ad1` in a separate worktree (disclosed in `docs/AUDIT.md`). The removed `.shift(1)` in `cnt_roll_7` made ridge look **better**: valid R² 0.8025 vs 0.6951 clean, test 0.7254 vs 0.6238. Only `test_rolling_mean_excludes_today` flagged it. A leak presents as an improvement, so the guardrail has to be a test, not a reviewer eyeballing metrics.

## Exercise 4: target transform

hgb fails because it was trained on 2011 and cannot predict above 2011's range, while 2012 ridership is ~65% higher. I tested four targets for hgb in `src/ex4_target.py` (`python -m src.ex4_target --target raw|log|diff|ratio|all`), on **validation only**, writing `reports/metrics_ex4.json`. `make train` and `reports/metrics.json` are unchanged, so the Results table above is still the untransformed run.

| hgb target | valid R² | valid MAE |
|------------|----------|-----------|
| raw `cnt` (sanity check: matches metrics.json) | 0.1936 | 1321.1 |
| `log1p(cnt)` | 0.1993 | 1303.2 |
| `cnt - cnt_roll_7` | 0.7261 | 704.5 |
| `cnt / cnt_roll_7` | **0.7638** | **657.1** |

`log1p` barely moves anything: it compresses the scale, but the trees still cannot predict outside the range they saw. Predicting relative to `cnt_roll_7` works because the anchor already carries the 2012 level, so the trees only have to learn the day's deviation from the trailing week, which looks similar in both years. The ratio target takes hgb from below persistence (0.4507) to above ridge (0.6951) on validation. I did not touch the test split to choose among these. The honest next step would be one test evaluation of the ratio model, reported next to the rest.

## Exercise 5

TODO.

## Attribution

Code changes were made with Claude Code 2.1.332 driving **qwen3.5:9b** locally via Ollama (model `bikeshare-coder`, 64k context, `num_ctx=65536`), in manual permission mode. Every agent edit was reviewed in the diff before acceptance. I wrote these tests myself after rejecting agent versions: `test_temp_lag_1_is_yesterdays_temp`, `test_encode_weather_rejects_unknown_labels`, and `test_raw_data_unchanged`. Documentation drafts (this report, `SEEDED_FAULTS.md`, `CLAUDE.md` additions) were drafted with Claude (claude.ai) and checked against the repo and `metrics.json`.

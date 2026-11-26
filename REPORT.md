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

TODO (see `docs/AUDIT.md`).

## Exercise 4: target transform

TODO.

## Exercise 5

TODO.

## Attribution

Code changes were made with Claude Code 2.1.332 driving **qwen3.5:9b** locally via Ollama (model `bikeshare-coder`, 64k context, `num_ctx=65536`), in manual permission mode. Every agent edit was reviewed in the diff before acceptance. I wrote these tests myself after rejecting agent versions: `test_temp_lag_1_is_yesterdays_temp`, `test_encode_weather_rejects_unknown_labels`, and `test_raw_data_unchanged`. Documentation drafts (this report, `SEEDED_FAULTS.md`, `CLAUDE.md` additions) were drafted with Claude (claude.ai) and checked against the repo and `metrics.json`.

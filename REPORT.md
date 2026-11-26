# Agentic Programming: bikeshare-open

## Results

All numbers come from `make all` with the pinned `requirements.txt`. **After** rows are `reports/metrics.json` as committed (15 features, including my `temp_lag_1`). **Before** rows are the same pipeline at commit `707a2c9` (14 features, before the feature). Train = 2011 (348 days), valid = H1 2012 (182), test = H2 2012 (184).

| Model | Features | Valid R² | Valid MAE | Test R² | Test MAE |
|-------|----------|----------|-----------|---------|----------|
| baseline_mean | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_mean | after | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| baseline_persistence | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| ridge | after | 0.6951 | 746.1 | 0.6238 | 876.6 |
| hgb | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| hgb | after | 0.1936 | 1321.1 | -0.5785 | 2036.7 |

The baselines do not use `temp_lag_1`, so their rows are identical before and after.

## Headline finding

The naive evaluation (`python -m src.leakage_demo`) gives R² = 1.000 and is invalid: `casual + registered == cnt` on every row, so the model learns addition. Under a temporal split the mean baseline scores -2.14 on test, because 2012 ridership is ~65% above the 2011 average it predicts. Ridge reaches **0.624 on test against a persistence baseline of 0.510, but loses to persistence on MAE (876.6 vs 840.1 rides)**. Gradient boosting is negative on test (-0.58) yet still beats the mean baseline. It fails because a tree cannot predict above the 2011 range. Adding `temp_lag_1` (yesterday's temperature) raised ridge's validation R² from 0.6475 to 0.6951 (+0.048, MAE 832.9 to 746.1), above the 0.01 noise floor, so I kept it. The decision was made on validation only. It slightly hurt hgb (validation 0.2185 to 0.1936).

## Exercise 4: target transformation

I tested four hgb targets in `src/ex4_target.py`, choosing on **validation only** (`reports/metrics_ex4.json`). Then I touched test **once**, for the winner only (`python -m src.ex4_target --target ratio --final`, `reports/metrics_ex4_final.json`). `reports/metrics.json` remains the untransformed pipeline.

| hgb target | Valid R² | Valid MAE | Test R² | Test MAE |
|------------|----------|-----------|---------|----------|
| raw `cnt` (matches metrics.json) | 0.1936 | 1321.1 | not run | not run |
| `log1p(cnt)` | 0.1993 | 1303.2 | not run | not run |
| `cnt - cnt_roll_7` | 0.7261 | 704.5 | not run | not run |
| `cnt / cnt_roll_7` | **0.7638** | **657.1** | **0.6287** | **837.5** |

`log1p` does nothing useful: it compresses the scale, but the trees still cannot leave the range they saw. Predicting relative to `cnt_roll_7` works because the anchor already carries the 2012 level, so the trees learn only the day's deviation from the trailing week. **Is it defensible?** Mostly yes. `cnt_roll_7` is known at prediction time (it shifts before it rolls, and `test_rolling_mean_excludes_today` enforces that), the choice was made on validation, and test was used once. But it does not show that trees are better here. On test the ratio model ties ridge (0.6287 vs 0.6238, inside the noise of 184 days). It also fell 0.135 from validation to test, and part of its gain is borrowed persistence: it is "last week's mean times a learned multiplier". I also applied the transform to hgb only, so ridge with the same target is untested. The honest claim is that the transform lets the tree compete with ridge, not that it wins.

## Exercise 5: ridge vs persistence

Ridge is worth deploying over "yesterday again", narrowly. On test, ridge's R² of 0.6238 against persistence's 0.5099 means it removes **23% of persistence's unexplained squared error** (1-R² falls from 0.490 to 0.376). On validation it wins both metrics clearly (R² 0.6951 vs 0.4507, MAE 746.1 vs 900.6, 17% lower). Its one loss is test MAE, by **36.5 rides (4.3%)**. Lower squared error with slightly higher absolute error means persistence is better on ordinary days and much worse on days when demand jumps, which are the days when yesterday is a bad guide (weather changes, holidays, Hurricane Sandy on 2012-10-29). Those are the days a rebalancing or staffing decision depends on, so I would pay 4% on the typical day to avoid the large misses. The conditions: keep persistence running alongside as a monitor, and drop ridge if its rolling MAE falls behind persistence's on new data. If the operational cost of error were linear and uniform across days, the test MAE would favor persistence and this verdict would flip.

## Attribution

**Model: qwen3.5:9b via Ollama (`bikeshare-coder`), 64k context (`num_ctx=65536`), driven by Claude Code 2.1.332 in manual permission mode. I did not switch models.** I also used Claude (claude.ai chat, not connected to the repo or the terminal) as a tutor. It drafted commands, tests and text that I pasted, ran and checked against the printed output. That work is listed separately below.

**Generated by the coding agent (qwen3.5:9b):**
- The `temp_lag_1` line in `src/features.py` (`54e113a`, via `/new-feature`).
- The fixes for seeded faults 1 (`d5990a4`), 2 (`27c4972`; its first attempt, `shift(LAG_WARMUP)`, was wrong and reverted) and 3 (`fce3256`; it dropped `sorted()` from the message).
- `agent/audit.py` was attempted but did not finish in ~53 minutes on the 9B model, so there is no `reports/audit.jsonl` (see `docs/AUDIT.md`).
- Rejected: its first `temp_lag_1` test (an always-false condition that could never fail), and its suggestion to update or remove the failing `encode_weather` test instead of restoring the `raise`.

**Drafted with Claude (chat), then run and checked by me:**
- The tests `test_temp_lag_1_is_yesterdays_temp`, `test_every_raw_column_is_classified`, `test_encode_weather_rejects_unknown_labels`, `test_raw_data_unchanged`.
- `SOURCE_COLS` / `UNUSED_COLS` in `src/config.py`, `.claude/skills/seed-fault/SKILL.md`, `src/ex4_target.py`.
- The text of this report, `docs/SEEDED_FAULTS.md`, `docs/AUDIT.md` and the `CLAUDE.md` additions.

**Unchanged starter:** the rest of the pipeline, the hook, the permission rules, the `leakage-auditor` subagent, `agent/audit.py` and the `new-feature` skill.

**Decisions that were mine** (each is a line in `docs/DECISIONS.md`):
- What to predict and what counts as leakage: kept the starter's exclusions (`casual`/`registered`, time indexes, `cnt_2d_bfr`).
- How to split (2011 / H1 2012 / H2 2012) and which baselines (mean and persistence), kept from the starter.
- Adding `temp_lag_1` and keeping it (+0.048 validation R²).
- Requiring every raw column to be classified, and how I classified the six it flagged.
- Adding the `encode_weather` test after finding that Fault 3 was invisible.
- Pinning the raw data's sha256 after Fault 4.
- The Exercise 4 transform, choosing it on validation, touching test once, and judging it a tie rather than a win.
- The Exercise 5 verdict.
- The `CLAUDE.md` additions and the `seed-fault` skill.
- Auditing my own commit, since I had no teammate.
- Whether the answer is believable. The leaky commit `6d19ad1` scored better than the real pipeline (ridge valid 0.8025 vs 0.6951), so I trust these numbers because tests pin the rules, not because they look good.

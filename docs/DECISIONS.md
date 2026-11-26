# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-25 · Added temp_lag_1 (yesterday's temperature). Availability: d-1 temperature is known before day d starts. Validation ridge R² 0.6475 → 0.6951 (+0.048), MAE 832.9 → 746.1. Above the 0.01 threshold, so kept. Decision made on validation only; test numbers printed by make train were not used.
- 2026-11-25 · Added test_every_raw_column_is_classified (tests/test_contract.py). First run flagged 6 unclassified raw columns. Classified holiday/workday/weather as SOURCE_COLS (re-encoded by features.py) and mnth/weekday/season as UNUSED_COLS (mnth and weekday restate dteday; season restates month). A new raw column now fails make test until classified. Verified the test goes red by removing "season".
- 2026-11-25 · Found that no test exercised encode_weather's raise: removing it would leave the suite green, because every label in the data is mapped. Added test_encode_weather_rejects_unknown_labels to tests/test_leakage.py (so the PostToolUse hook also runs it).
- 2026-11-25 · Fault 4: the agent's Bash cp into data/raw/ was blocked by the deny rule (Claude Code 2.1.332), but the same cp run outside the agent went through and make test stayed green (17 passed). Added test_raw_data_unchanged (sha256 pin) to tests/test_contract.py; verified it goes red on the tampered file.
- 2026-11-25 · Exercise 4: target transforms for hgb live in src/ex4_target.py (flag --target), validation only, output reports/metrics_ex4.json; reports/metrics.json stays the untransformed run. ratio to cnt_roll_7 won (valid R² 0.7638 vs raw 0.1936); log1p did not help (0.1993) because it does not remove the level shift.
- 2026-11-25 · Exercise 4 final: chose ratio-to-cnt_roll_7 on validation, then touched test once (python -m src.ex4_target --target ratio --final): hgb test R² 0.6287 / MAE 837.5 vs ridge 0.6238 / 876.6. Defensible (anchor is known at prediction time and is tested by test_rolling_mean_excludes_today; chosen on validation only) but it ties ridge rather than beating it, and part of the gain is borrowed persistence. Output in reports/metrics_ex4_final.json.
- 2026-11-25 · Exercise 5: ridge is worth deploying over persistence, narrowly: on test it removes 23% of persistence's unexplained squared error (1-R² 0.490 -> 0.376) and on validation it wins both R² and MAE (746.1 vs 900.6); it loses test MAE by 36.5 rides (4.3%).
- 2026-11-25 · CLAUDE.md: added a 9-line "Skills and guardrails" section (seed-fault skill, hook rule "fix the code, never the test", raw-data hash, column classification). 51 lines total.
- 2026-11-25 · Exercise 3: no teammate, so audited my own leaky commit 6d19ad1 in a git worktree; disclosed in docs/AUDIT.md. The leak raised ridge valid R² 0.6951 -> 0.8025.
- 2026-11-25 · Wrote the seed-fault skill because break/record/restore was repeated for four faults. Added Grep to its allowed-tools after the first run fell back to bash grep.
- 2026-11-25 · Exercise 3 agent runs: stopped agent/audit.py after 53 min (no output) and the leakage-auditor subagent after ~4 min to travel. Documented as incomplete in docs/AUDIT.md rather than committing a partial or hand-written audit.jsonl.

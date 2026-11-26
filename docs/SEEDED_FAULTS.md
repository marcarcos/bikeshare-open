# Seeded faults

Four faults, each committed broken and then fixed with the agent (qwen3.5:9b via Ollama, model `bikeshare-coder`, Claude Code in manual permission mode). The guardrail under test: the PostToolUse hook `.claude/hooks/check_leakage.sh`, which re-runs `tests/test_leakage.py` after every agent edit to `src/` and exits 2 with the failure on stderr, plus the deny rules in `.claude/settings.json`.

| # | Fault | Caught by | Agent turns to fix | Broken / fixed commit |
|---|-------|-----------|--------------------|-----------------------|
| 1 | `casual` (target leak) let through `feature_columns` | hook: `test_no_forbidden_features` | 1 | `fde1407` / `d5990a4` |
| 2 | `.shift(1)` removed from `cnt_roll_7` (rolling mean includes today) | hook: `test_rolling_mean_excludes_today` (4389.0 vs 4414.857) | 2 (first fix wrong) | `6d19ad1` / `27c4972` |
| 3 | `raise` removed from `encode_weather` (unknown labels become NaN, rows silently dropped) | nothing at first; hook after we added `test_encode_weather_rejects_unknown_labels` | 1 | `162ca0d` / `fce3256` |
| 4 | `data/raw/bike_daily.csv` overwritten with a tampered copy (temp+5 on row 100) | agent: deny rule blocked it. Human: nothing, until we added `test_raw_data_unchanged` | n/a | test added after the run (see git log) |

## Fault 1: target leakage through `feature_columns`

Broke `feature_columns` so `casual` (part of `cnt = casual + registered`) passed the FORBIDDEN filter. The first agent edit to `src/features.py` triggered the hook, which exited 2 with `test_no_forbidden_features` failing. The agent read the stderr and restored the filter in one turn. This is the case the hook was built for: a leak becomes a red test the agent sees immediately, not a suspiciously good R² later.

## Fault 2: rolling mean includes today

Removed `.shift(1)` from `cnt_roll_7`, so the 7-day mean includes the day being predicted. The hook went red on `test_rolling_mean_excludes_today` (got 4389.0, expected 4414.857). **The agent's first fix was wrong:** it changed the code to `shift(LAG_WARMUP)`, which silences nothing and is still incorrect (it shifts by 7 days, not 1). That edit was accidentally accepted, then reverted with `git checkout`. On turn 2 the agent restored `.shift(1)` and the hook went green. Lesson: a red-to-green hook does not mean the fix is right; every diff still needs reading.

## Fault 3: validation `raise` removed

Removed the `raise ValueError` for unmapped weather labels. **No existing test covered this**: the starter suite stayed green, so the hook had nothing to catch. We added `test_encode_weather_rejects_unknown_labels` (commit `8b6cd92`) before seeding the fault. After that the hook went red ("DID NOT RAISE ValueError", 1 failed / 8 passed). **The agent's recap suggested updating or removing the failing test**, which would have hidden the fault. We rejected that and asked it to restore the raise. Fixed in 1 turn, but the message dropped `sorted()` (functionally correct, not identical to the original). Lesson: the hook only protects what the tests cover, and a small model will offer to weaken the test instead of fixing the code.

## Fault 4: raw data modified

1. **Through the agent:** asked it to run `cp /tmp/bike_daily_tampered.csv data/raw/bike_daily.csv`. Claude Code 2.1.332 refused: "permission denied - rule from shared project settings". The deny rules blocked a Bash `cp`, contrary to the lesson's claim that `Write`/`Edit` deny rules do not cover Bash. (Claude Code also warned that the `Write(./data/raw/**)` rule never matches.)
2. **Outside the agent:** ran the same `cp` in a normal shell. The sha256 changed to `c179234567cd...`, and `make test` stayed green (17 passed). Nothing in the repo noticed.
3. **Fix:** added `test_raw_data_unchanged` to `tests/test_contract.py`, pinning sha256 `a6bed1577f6e4de5...`. Re-ran the tampered copy: 1 failed with `raw data modified`. Restored with `git checkout`: 18 passed. Lesson: deny rules and hooks only govern the agent's tool calls. Integrity of `data/raw/` has to be a test, so it holds no matter who or what changes the file.

## Evidence (verbatim, from ~/bikeshare-notes)

### fault1_diff

    diff --git a/src/features.py b/src/features.py
    index eece854..cd12868 100644
    --- a/src/features.py
    +++ b/src/features.py
    @@ -82,7 +82,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     def feature_columns(df: pd.DataFrame) -> list[str]:
         """Numeric columns that are safe to feed the model."""
         numeric = df.select_dtypes(include="number").columns
    -    return [c for c in numeric if c not in FORBIDDEN]
    +    return [c for c in numeric if c not in FORBIDDEN] + ["casual"]
     
     
     if __name__ == "__main__":

### fault1_hook_stderr

    PostToolUse:Edit hook reported a problem
    [${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /Users/marceloarcos/Documents/DSC180A/Methodology-6/bikeshare-open/src/features.py:
        def test_no_forbidden_features(feats):
            cols = set(feature_columns(feats))
    >       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
    E       AssertionError: forbidden columns in feature set: {'casual'}
    tests/test_leakage.py:32: AssertionError
    FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
    1 failed, 7 passed in 0.57s

### fault1_tests_red

    ......F.........                                                         [100%]
    =================================== FAILURES ===================================
    __________________________ test_no_forbidden_features __________________________
    
    feats =         dteday  instant  season  ...  temp_lag_1 cnt_lag_7   cnt_roll_7
    0   2011-01-10     10.0  WINTER  ...   -1.4983...   1787.0  1530.142857
    713 2012-12-31    731.0  WINTER  ...    4.024151     920.0  1531.428571
    
    [714 rows x 29 columns]
    
        def test_no_forbidden_features(feats):
            """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
            construction, so this cannot discover a *new* leaky column. What it
            catches is someone editing feature_columns() or FORBIDDEN -- which is
            exactly the fault the Step 7 hook demonstrates."""
            cols = set(feature_columns(feats))
    >       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
    E       AssertionError: forbidden columns in feature set: {'casual'}
    E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'dayofweek', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})
    
    tests/test_leakage.py:32: AssertionError
    =========================== short test summary info ============================
    FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
    1 failed, 15 passed in 1.62s

### fault2_diff

    diff --git a/src/features.py b/src/features.py
    index eece854..0f13401 100644
    --- a/src/features.py
    +++ b/src/features.py
    @@ -74,7 +74,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
         out["cnt_lag_1"] = out[TARGET].shift(1)
         out["temp_lag_1"] = out.temp.shift(1)
         out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
    -    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
    +    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
     
         return out.dropna().reset_index(drop=True)
     

### fault2_hook_stderr

    (PostToolUse hook on Edit of src/features.py, re-running tests/test_leakage.py)
            by_date = feats.set_index("dteday")[TARGET]
            date = feats.dteday.iloc[200]
            window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
            if all(d in by_date.index for d in window):
                expected = sum(by_date[d] for d in window) / 7
    >           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
    E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
    E             comparison failed
    E             Obtained: 4389.0
    E             Expected: 4414.857142857143 ± 0.00441486
    tests/test_leakage.py:58: AssertionError
    FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
    1 failed, 7 passed in 0.52s

### fault2_tests_red

    .........F......                                                         [100%]
    =================================== FAILURES ===================================
    _______________________ test_rolling_mean_excludes_today _______________________
    
    feats =         dteday  instant  season  ...  temp_lag_1 cnt_lag_7   cnt_roll_7
    0   2011-01-10     10.0  WINTER  ...   -1.4983...   1787.0  1531.428571
    713 2012-12-31    731.0  WINTER  ...    4.024151     920.0  1789.857143
    
    [714 rows x 29 columns]
    
        def test_rolling_mean_excludes_today(feats):
            """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
            by_date = feats.set_index("dteday")[TARGET]
            date = feats.dteday.iloc[200]
            window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
            if all(d in by_date.index for d in window):
                expected = sum(by_date[d] for d in window) / 7
    >           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
    E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
    E             
    E             comparison failed
    E             Obtained: 4389.0
    E             Expected: 4414.857142857143 ± 0.00441486
    
    tests/test_leakage.py:58: AssertionError
    =========================== short test summary info ============================
    FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
    1 failed, 15 passed in 1.78s

### fault2_wrong_fix_diff

    diff --git a/src/features.py b/src/features.py
    index 0f13401..88b20e3 100644
    --- a/src/features.py
    +++ b/src/features.py
    @@ -74,7 +74,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
         out["cnt_lag_1"] = out[TARGET].shift(1)
         out["temp_lag_1"] = out.temp.shift(1)
         out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
    -    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
    +    out["cnt_roll_7"] = out[TARGET].shift(LAG_WARMUP).rolling(LAG_WARMUP).mean()
     
         return out.dropna().reset_index(drop=True)
     

### fault3_diff

    diff --git a/src/features.py b/src/features.py
    index eece854..34778b2 100644
    --- a/src/features.py
    +++ b/src/features.py
    @@ -26,8 +26,6 @@ def encode_weather(series: pd.Series) -> pd.Series:
         """
         known = series.dropna()
         unknown = set(known.unique()) - set(WEATHER_ORDER)
    -    if unknown:
    -        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
         return series.map(WEATHER_ORDER).astype(float)
     
     

### fault3_hook_stderr

    (PostToolUse hook on Edit of src/features.py, re-running tests/test_leakage.py)
            """encode_weather must fail loudly on an unseen label. Without the raise,
            the label maps to NaN and dropna() silently deletes those days."""
            from src.features import encode_weather
    >       with pytest.raises(ValueError, match="unmapped weather labels"):
    E       Failed: DID NOT RAISE ValueError
    
    tests/test_leakage.py:80: Failed
    =========================== short test summary info ============================
    FAILED tests/test_leakage.py::test_encode_weather_rejects_unknown_labels - Fa...
    1 failed, 8 passed in 0.57s

### fault3_tests_red

    .............F...                                                        [100%]
    =================================== FAILURES ===================================
    __________________ test_encode_weather_rejects_unknown_labels __________________
    
        def test_encode_weather_rejects_unknown_labels():
            """encode_weather must fail loudly on an unseen label. Without the raise,
            the label maps to NaN and dropna() silently deletes those days."""
            from src.features import encode_weather
    >       with pytest.raises(ValueError, match="unmapped weather labels"):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    E       Failed: DID NOT RAISE ValueError
    
    tests/test_leakage.py:80: Failed
    =========================== short test summary info ============================
    FAILED tests/test_leakage.py::test_encode_weather_rejects_unknown_labels - Fa...
    1 failed, 16 passed in 1.57s

### fault4_notes

    Fault 4 attempt 1 (agent, Claude Code 2.1.332): asked agent to run
      cp /tmp/bike_daily_tampered.csv data/raw/bike_daily.csv
    Result: "Not run - permission denied - rule from shared project settings".
    The deny rule DID block a Bash cp, contrary to the lesson's claim. No hook fired (nothing ran).

### fault4_hash_after

    c179234567cd68fc7a1002b269c8a475e9320b4a8a45c592630eeecc3de78304  data/raw/bike_daily.csv

### fault4_tests

    .................                                                        [100%]
    17 passed in 1.66s

### fault4_hash_test_red

    tests/test_contract.py:78: AssertionError
    =========================== short test summary info ============================
    FAILED tests/test_contract.py::test_raw_data_unchanged - AssertionError: raw ...
    1 failed, 5 passed in 1.09s

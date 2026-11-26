"""Exercise 4: does a target transform fix hgb's extrapolation failure?

hgb trained on 2011 cannot predict above 2011's range, and 2012 is ~65%
higher. Transforms that predict relative to cnt_roll_7 (which already
carries the current level) should let trees move with the level.

Validation only. Never tuned on test. Does not touch reports/metrics.json.
Run: python -m src.ex4_target [--target raw|log|diff|ratio|all]
"""
import argparse
import json

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, r2_score

from src.config import METRICS, PROCESSED, TARGET
from src.features import feature_columns
from src.train import MODELS, temporal_split

ANCHOR = "cnt_roll_7"
OUT = METRICS.parent / "metrics_ex4.json"

# name -> (forward: y, X -> fit target, inverse: pred, X -> cnt)
TRANSFORMS = {
    "raw": (lambda y, X: y, lambda p, X: p),
    "log": (lambda y, X: np.log1p(y), lambda p, X: np.expm1(p)),
    "diff": (lambda y, X: y - X[ANCHOR], lambda p, X: p + X[ANCHOR].to_numpy()),
    "ratio": (lambda y, X: y / X[ANCHOR], lambda p, X: p * X[ANCHOR].to_numpy()),
}


def run(names):
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, _ = temporal_split(df)
    results = {}
    for name in names:
        fwd, inv = TRANSFORMS[name]
        model = clone(MODELS["hgb"])
        model.fit(train[cols], fwd(train[TARGET], train))
        pred = inv(model.predict(valid[cols]), valid)
        results[name] = {"valid": {
            "r2": round(float(r2_score(valid[TARGET], pred)), 4),
            "mae": round(float(mean_absolute_error(valid[TARGET], pred)), 1),
        }}
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="all", choices=[*TRANSFORMS, "all"])
    args = ap.parse_args()
    names = list(TRANSFORMS) if args.target == "all" else [args.target]
    res = {"model": "hgb", "split": "valid", "anchor": ANCHOR, "results": run(names)}
    OUT.write_text(json.dumps(res, indent=2))
    best = max(res["results"], key=lambda k: res["results"][k]["valid"]["r2"])
    print(json.dumps(res["results"], indent=2))
    print(f"OK ex4: {len(names)} targets, best on valid = {best}, wrote {OUT.name}")

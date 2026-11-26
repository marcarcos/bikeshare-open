"""Exercise 4: does a target transform fix hgb's extrapolation failure?

hgb trained on 2011 cannot predict above 2011's range, and 2012 is ~65%
higher. Transforms that predict relative to cnt_roll_7 (known at
prediction time: it is shifted before it rolls) let the trees move with
the level.

Choose on validation:   python -m src.ex4_target            (all targets)
Touch test once:        python -m src.ex4_target --target ratio --final
Neither run touches reports/metrics.json (the untransformed pipeline).
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
OUT_FINAL = METRICS.parent / "metrics_ex4_final.json"

# name -> (forward: y, X -> fit target, inverse: pred, X -> cnt)
TRANSFORMS = {
    "raw": (lambda y, X: y, lambda p, X: p),
    "log": (lambda y, X: np.log1p(y), lambda p, X: np.expm1(p)),
    "diff": (lambda y, X: y - X[ANCHOR], lambda p, X: p + X[ANCHOR].to_numpy()),
    "ratio": (lambda y, X: y / X[ANCHOR], lambda p, X: p * X[ANCHOR].to_numpy()),
}


def score(y, pred):
    return {"r2": round(float(r2_score(y, pred)), 4),
            "mae": round(float(mean_absolute_error(y, pred)), 1)}


def run(names, final=False):
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)
    results = {}
    for name in names:
        fwd, inv = TRANSFORMS[name]
        model = clone(MODELS["hgb"])
        model.fit(train[cols], fwd(train[TARGET], train))
        entry = {"valid": score(valid[TARGET], inv(model.predict(valid[cols]), valid))}
        if final:
            entry["test"] = score(test[TARGET], inv(model.predict(test[cols]), test))
        results[name] = entry
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="all", choices=[*TRANSFORMS, "all"])
    ap.add_argument("--final", action="store_true",
                    help="also score the test split; one chosen target only")
    args = ap.parse_args()
    if args.final and args.target == "all":
        ap.error("--final scores test once: pick the one target chosen on validation")
    names = list(TRANSFORMS) if args.target == "all" else [args.target]
    res = {"model": "hgb", "anchor": ANCHOR, "final": args.final,
           "results": run(names, args.final)}
    out = OUT_FINAL if args.final else OUT
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps(res["results"], indent=2))
    print(f"OK ex4: {len(names)} target(s), final={args.final}, wrote {out.name}")

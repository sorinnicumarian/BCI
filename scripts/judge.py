# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "scikit-learn", "pyserial"]
# ///
"""Offline judge: replay recorded datasets through a classifier, no hardware needed.

Usage:
  uv run scripts/judge.py                 # all methods, all 4-class datasets
  uv run scripts/judge.py --method live   # only the rule in python_solution/predict.py
  uv run scripts/judge.py --smoke         # fast check for the test gate (one dataset)
  uv run scripts/judge.py --save python_solution/model4.pkl [--train-on 09]
                                          # fit logreg on ALL windows of one dataset, for BCI_MODEL

Metric: 4-class balanced accuracy (chance = 25%), chronological split inside each
session (train on the first 70% of every file, test on the last 30%, with a 1 s gap
so overlapping windows don't leak). Reported per dataset and as the mean over
datasets 06, 08, 09 (the 4-class sessions). "live" needs no training; it is scored
on the same test part so all methods are comparable.
"""
import argparse
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "python_solution"))
import predict  # noqa: E402  (band_powers, FS, WIN, STEP, BETA_THRESH)

DATA = os.path.join(ROOT, "artefacts", "data")
DATASETS = ["06", "08", "09"]
CLASSES = ["RelaxUp", "FocusDown", "CBRight", "SingLeft"]
TRAIN_FRAC = 0.7
GAP = predict.WIN  # samples dropped between train and test part


def label_of(fname):
    f = fname.lower()
    if "relax" in f and "up" in f:
        return 0
    if "focus" in f and "down" in f:
        return 1
    if "count_backwards" in f and "right" in f:
        return 2
    if "sing" in f and "left" in f:
        return 3
    return None


def load(ds):
    out = []
    for f in sorted(os.listdir(DATA)):
        if f.startswith(ds + "_") and f.endswith(".csv"):
            y = label_of(f)
            if y is not None:
                x = np.loadtxt(os.path.join(DATA, f), delimiter=",", skiprows=1, usecols=1)
                out.append((y, x))
    return out


def valid(w):
    # same artifact rejection as predict.py main loop
    return w.std() > 0.5 and w.max() < 1010 and w.min() > 10


def windows(x):
    for s in range(0, len(x) - predict.WIN + 1, predict.STEP):
        w = x[s:s + predict.WIN]
        if valid(w):
            yield w


features = predict.features


def split(x):
    n = int(len(x) * TRAIN_FRAC)
    return x[:n], x[n + GAP:]


def build(sessions):
    Xtr, ytr, Xte, yte, Wte = [], [], [], [], []
    for y, x in sessions:
        tr, te = split(x)
        for w in windows(tr):
            Xtr.append(features(w)); ytr.append(y)
        for w in windows(te):
            Xte.append(features(w)); yte.append(y); Wte.append(w)
    return np.array(Xtr), np.array(ytr), np.array(Xte), np.array(yte), Wte


def m_live(Xtr, ytr, Xte):
    # predict.py rule: beta% < BETA_THRESH -> RelaxUp (0) else FocusDown (1)
    return np.where(Xte[:, 3] < predict.BETA_THRESH, 0, 1)


def m_ml4(Xtr, ytr, Xte):
    from sklearn.ensemble import RandomForestClassifier
    clf = RandomForestClassifier(n_estimators=200, min_samples_leaf=3, random_state=0, n_jobs=-1)
    return clf.fit(Xtr, ytr).predict(Xte)


def m_logreg(Xtr, ytr, Xte):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    return clf.fit(Xtr, ytr).predict(Xte)


METHODS = {"live": m_live, "logreg": m_logreg, "ml4": m_ml4}


def save(path, ds):
    import pickle
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    X, y = [], []
    for c, x in load(ds):
        for w in windows(x):
            X.append(features(w)); y.append(c)
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(X, y)
    with open(path, "wb") as f:
        pickle.dump(clf, f)
    print(f"saved logreg trained on dataset {ds} ({len(y)} windows) -> {path}")


def bal_acc(y, p):
    return float(np.mean([np.mean(p[y == c] == c) for c in np.unique(y)]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=list(METHODS), action="append")
    ap.add_argument("--smoke", action="store_true", help="one dataset, fast")
    ap.add_argument("--save", help="fit logreg on all windows of --train-on and pickle it here")
    ap.add_argument("--train-on", default="09")
    args = ap.parse_args()
    if args.save:
        return save(args.save, args.train_on)
    methods = args.method or list(METHODS)
    datasets = ["08"] if args.smoke else DATASETS

    t0 = time.time()
    data = {ds: build(load(ds)) for ds in datasets}
    for ds, (Xtr, ytr, Xte, yte, _) in data.items():
        if len(Xte) == 0 or len(set(yte)) < 4:
            sys.exit(f"judge: dataset {ds} has no usable 4-class test windows")

    print(f"{'method':8s} " + " ".join(f"ds{ds:>4s}" for ds in datasets) + "   mean   (chance 0.25)")
    for m in methods:
        scores = []
        for ds in datasets:
            Xtr, ytr, Xte, yte, _ = data[ds]
            scores.append(bal_acc(yte, METHODS[m](Xtr, ytr, Xte)))
        print(f"{m:8s} " + " ".join(f"{s:6.3f}" for s in scores) + f"  {np.mean(scores):.3f}")
    print(f"({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()

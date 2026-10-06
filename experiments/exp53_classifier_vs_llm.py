"""Exp 53 — classic classifier vs the exp52 LLM on the same eval.

Trains one gradient-boosted tree per task (T1-T5) on the same view-calibrated
synthetic cases exp52 used (exp52_rlvr_dataset.case_fields/case_labels), with
the same record fields the LLM sees, and scores it on the exp30 v1.1 test
set with the same scorer (incl. chance-corrected skill). Real cases are only
used for scoring. CPU only.

Usage: python3 experiments/exp53_classifier_vs_llm.py
"""
import json
import random
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments"))
import exp52_rlvr_dataset as E  # noqa: E402

FEATS = ["raw_hhsize", "cert_hhsize", "raw_gross", "raw_net", "raw_ernded", "rep_csup_ded",
         "rep_depcare_ded", "rep_med_exp", "rep_shel_ded", "verif_unit_size", "verif_hhsize",
         "verif_gross", "verif_net", "verif_earned", "verif_unearned", "std_ded", "ernd_ded",
         "med_ded", "shel_ded", "tot_ded", "csup_ded", "shel_exp", "has_child", "has_elder",
         "n_elder", "n_disab"]
DIFFS = [("raw_gross", "verif_gross"), ("raw_net", "verif_net"), ("raw_hhsize", "verif_hhsize"),
         ("raw_ernded", "ernd_ded"), ("rep_shel_ded", "shel_ded")]


def vec(f):
    x = [np.nan if f.get(k) is None else float(f[k]) for k in FEATS]
    x += [np.nan if f.get(a) is None or f.get(b) is None else float(f[a]) - float(f[b]) for a, b in DIFFS]
    return x


def main():
    rng = random.Random(53)
    cases = E.gen_synth(30000, 52)
    rows = [(E.case_fields(c), E.case_labels(c)) for c in cases]
    E.apply_view_calibration(rows, json.loads(E.CALIBRATION.read_text()), rng)
    by = {f: [r for r in rows if r[1]["t2"] == f] for f in E.FINDING.values()}
    rows = sum((rng.sample(v, min(len(v), 4000)) for v in by.values()), [])  # balanced like exp52
    X = np.array([vec(f) for f, _ in rows])
    items = [i for i in json.loads((E.EVAL / "items.json").read_text())
             if i["split"] in ("test_main", "test_2024")]
    Xt = np.array([vec(i["fields"]) for i in items])
    preds = {i["item_id"]: {} for i in items}
    for t in ("t1", "t2", "t3", "t4", "t5"):
        idx = [k for k, (_, lab) in enumerate(rows) if lab[t] is not None]
        y = [rows[k][1][t] for k in idx]
        clf = HistGradientBoostingClassifier(random_state=53).fit(X[idx], y)
        for it, p in zip(items, clf.predict(Xt)):
            preds[it["item_id"]][t] = str(p)
    out = E.EVAL / "preds_exp53_gbm_synthetic_class.jsonl"
    with open(out, "w") as fh:
        for iid, p in preds.items():
            fh.write(json.dumps({"item_id": iid, "kind": "class", "parsed": p, "parse_ok": True}) + "\n")
    print(f"wrote {out} ({len(rows)} training cases)")


if __name__ == "__main__":
    main()

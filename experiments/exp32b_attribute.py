#!/usr/bin/env python3
"""exp32 follow-up: attribute the depcare regression.

B-final (senior fix + re-measured matrix + re-measured kid-weight) regressed
depcare 0.96x -> 0.78x vs the exp31 baseline. 2x2 ablation on seed 7, 20k:
  B0: senior fix + committed matrix + committed kid-weight (= run-1 arm B)
  B1: senior fix + committed matrix + NEW kid-weight
  B2: senior fix + NEW matrix + committed kid-weight
  B3: senior fix + NEW matrix + NEW kid-weight (= B-final)
Plus: keep-rate measurement under legacy-senior + mechanisms-ON, to separate
the senior-fix effect from the dollar-mechanism effect on the keep shifts.
"""
import copy
import json
import random
import sys
from collections import Counter
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP_DIR.parent / "src"))
from synth import dollar_mech, errors, household  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402
from synth.distutil import load_dist  # noqa: E402

sys.path.insert(0, str(EXP_DIR))
import exp32_medical_senior as e32  # noqa: E402 (reuses mixes/gen/real/patches)

NEW_KID = {"no_earner_nonsenior": 1.808, "earner_nonsenior": 1.843,
           "no_earner_senior": 3.671, "earner_senior": 4.391}
NEW_MATRIX = json.load(open(EXP_DIR / "exp32_matrix.json"))["matrix"]


def main():
    # committed matrix / kid-weight: read from git HEAD (adoptions are
    # uncommitted in the working tree)
    import subprocess
    head_errors = subprocess.run(
        ["git", "show", "HEAD:src/synth/errors.py"], cwd=EXP_DIR.parent,
        capture_output=True, text=True).stdout
    import re
    m = re.search(r"MATERIALIZATION_MATRIX = \{.*?\n\}\n", head_errors,
                  re.DOTALL).group(0)
    ns = {}
    exec(m, {}, ns)
    committed_matrix = ns["MATERIALIZATION_MATRIX"]
    k = re.search(r"_DEPCARE_KID_WEIGHT = \{.*?\n\}\n", head_errors,
                  re.DOTALL).group(0)
    ns2 = {}
    exec(k, {}, ns2)
    committed_kid = ns2["_DEPCARE_KID_WEIGHT"]

    dist = load_dist(str(EXP_DIR / "dist.json"))
    real = e32.real_aggregates(str(e32.REAL))

    arms = {
        "B0": (committed_matrix, committed_kid),
        "B1": (committed_matrix, NEW_KID),
        "B2": (NEW_MATRIX, committed_kid),
        "B3": (NEW_MATRIX, NEW_KID),
    }
    base = None
    for name, (mat, kid) in arms.items():
        errors.MATERIALIZATION_MATRIX = {b: dict(v) for b, v in mat.items()}
        errors._DEPCARE_KID_WEIGHT = dict(kid)
        d_mech = dollar_mech.enable_adopted(dist)
        try:
            m_ = e32.mixes(e32.gen_cases(20000, 7, d_mech))
        finally:
            dollar_mech.disable()
        if base is None:
            # B0 is the reference only for cross-check; real baseline is arm A
            pass
        dep = m_["per_case"]["depcare"] / real["per_case"]["depcare"]
        med = m_["per_case"]["medical"] / real["per_case"]["medical"]
        print(f"{name}: depcare={dep:.2f}x medical={med:.2f}x "
              f"L1={e32.l1(m_['finding'], real['finding']):.3f} "
              f"le56={m_['le56']:.2f}", flush=True)

    # keep-rate measurement under LEGACY senior + mechanisms ON
    print("\nkeep rates: legacy-senior + mech ON  vs  (b)=senior-fix + mech ON"
          "  vs  committed (legacy-senior + mech OFF, exp29)")
    with e32.legacy_senior():
        e32._KR_DRAWN.clear()
        e32._KR_RECORDED.clear()
        d_mech = dollar_mech.enable_adopted(dist)
        errors._inject_persistent = e32._kr_ip
        try:
            e32.gen_cases(150000, 11, d_mech)
        finally:
            errors._inject_persistent = e32._ORIG_IP
            dollar_mech.disable()
    print(f"  {'bucket':<10}" + "".join(f"{s:>26}" for s in e32.STRATA))
    n_ba = n_ac = 0
    for b in e32.BUCKETS:
        row = f"  {b:<10}"
        for s in e32.STRATA:
            d = e32._KR_DRAWN[(b, s)]
            r = e32._KR_RECORDED[(b, s)]
            ma = round(min(1.0, max(0.02, r / d if d else 1.0)), 3)
            mb = NEW_MATRIX[b][s]
            mc = committed_matrix[b][s]
            dba = mb - ma
            dac = ma - mc
            if abs(dba) >= 0.05:
                n_ba += 1
            if abs(dac) >= 0.05:
                n_ac += 1
            row += (f"{ma:>6.3f}(b-a{dba:>+6.3f},a-c{dac:>+6.3f})")
        print(row)
    print(f"  cells |b-a|>=0.05 (senior-fix effect): {n_ba}/32")
    print(f"  cells |a-c|>=0.05 (mechanism effect):  {n_ac}/32")


if __name__ == "__main__":
    main()

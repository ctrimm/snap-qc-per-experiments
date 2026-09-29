"""exp31 helper: render the adopted-calibration constants block for
src/synth/dollar_mech.py from experiments/exp31_capture_A.json.

Folds the direction-balance boosts into dir_weight (the same operation as
dollar_mech.apply_direction_balance, which rounds to 4 decimals), so the
module default is the FINAL calibrated table.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
cap = json.loads((ROOT / "exp31_capture_A.json").read_text())

eff = cap["eff_new"]
boosts = cap["boosts"]
boost_o, boost_u = boosts["over"], boosts["under"]

dir_w = {}
for b, w in eff["dir_weight"].items():
    w2 = dict(w)
    if "over" in w2:
        w2["over"] = round(w2["over"] * boost_o, 4)
    if "under" in w2:
        w2["under"] = round(w2["under"] * boost_u, 4)
    dir_w[b] = w2

final_eff = {"bucket": eff["bucket"],
             "dir_materialization": eff["dir_materialization"],
             "dir_weight": dir_w}

under_scale = {int(k): v for k, v in cap["under_scales"].items()}
p97 = {b: v for b, v in cap["coins97"].items()}
phase1 = cap["phase1_coins"]
vpc = cap["v_per_case"]
unit_factor = cap["unit_factor"]

def _fmt_dict(d):
    return "{" + ", ".join(f"{k!r}: {v}" for k, v in sorted(d.items(),
                                                           key=lambda kv: str(kv[0]))) + "}"


print(f"# fitted values (exp26 seed set A; re-fit on seed set B agrees "
      f"within tolerance -- see experiments/exp31_adopt_dollar.md)")
print(f"EXP31_UNDER_SCALE = {_fmt_dict(under_scale)}")
print(f"EXP31_VARIANCES_PER_CASE = {round(vpc, 4)}")
print(f"EXP31_UNIT_FACTOR_NOTE = {round(unit_factor, 4)}  "
      f"# informational: adopted_dist re-derives via the helper")
print(f"EXP31_EFFECTIVENESS = {json.dumps(final_eff, indent=1)}")
print(f"EXP31_P97_COINS = {_fmt_dict(p97)}")
print(f"EXP31_PHASE1_COINS = {_fmt_dict(phase1)}")

"""exp31 helper (run once): append the adopted-calibration section to
src/synth/dollar_mech.py, with constants rendered from
experiments/exp31_capture_A.json (direction-balance boosts folded into
dir_weight, exactly as apply_direction_balance does)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
cap = json.loads((ROOT / "exp31_capture_A.json").read_text())

eff = cap["eff_new"]
boosts = cap["boosts"]
dir_w = {}
for b, w in eff["dir_weight"].items():
    w2 = dict(w)
    if "over" in w2:
        w2["over"] = round(w2["over"] * boosts["over"], 4)
    if "under" in w2:
        w2["under"] = round(w2["under"] * boosts["under"], 4)
    dir_w[b] = w2
final_eff = {"bucket": eff["bucket"],
             "dir_materialization": eff["dir_materialization"],
             "dir_weight": dir_w}

under_scale = {int(k): v for k, v in cap["under_scales"].items()}
p97 = dict(cap["coins97"])
phase1 = dict(cap["phase1_coins"])
vpc = round(cap["v_per_case"], 4)
unit_factor = round(cap["unit_factor"], 4)

PROSE = '''# --------------------------------------------------------------------------
# exp31: adopted calibration -- the exp26 recalibration as module defaults
# --------------------------------------------------------------------------
# The mechanisms collapse without the recalibration: enable() alone (no
# fitted coins / scales / effectiveness) gives finding L1 0.103 (exp31
# measured). These constants are the exp26 recalibration re-fitted on the
# CURRENT generator state -- exp24 draw defaults (ZERO_BASE_WEIGHT={} +
# exp29 re-measured MATERIALIZATION_MATRIX), exp29 sampler (BASE_POSITIVITY),
# exp29 97-coins, exp28 kid-weight/57-weights -- seed set A (exp26's exact
# seeds: pre-pass 5000, eff 11, 97-cal 21, boost 31). A re-fit on seed set
# B (5001/13/23/33) agrees within tolerance: boosts +/-0.01, phase-1 coins
# +/-0.025, 97 coins +/-0.011, unit-bucket factor +/-0.002, V +/-1.2%; the
# noisiest fitted values are the nature-44 under scale (0.641 vs 0.759) and
# rare-bucket dir_weight cells (medical/depcare/sua, up to 0.141). Full
# comparison: experiments/exp31_adopt_dollar.md.
#
# BRITTLENESS (measured): these are fitted to one generator state. Exp26's
# published values (fitted before exp29's matrix re-measurement) differ from
# the re-fit above (boosts 0.686->0.664, phase-1 coins ~0.02), so if the draw
# defaults, the materialization matrix, or the sampler change, re-run
# `python3 experiments/exp31_adopt_dollar.py capture` and re-render this
# section with experiments/exp31_render_constants.py. Design (b) -- persisted
# fitted values -- was chosen over adaptive re-fitting inside enable() on
# measured evidence: the recalibration needs ~150k case-generations per
# invocation, and its measurement noise would make seeded runs
# non-reproducible.
'''

block = PROSE
block += f"# mechanism-4 coarse-under scales (real_median / synth_median, clipped [0.25, 1.0])\n"
block += f"EXP31_UNDER_SCALE = {under_scale}\n\n"
block += (f"# recorded variances per case in the mechanism-on pre-pass; feeds the\n"
          f"# unit-bucket double-counting correction via apply_unit_bucket_correction\n"
          f"# (re-derives the factor {unit_factor} on the current dist)\n")
block += f"EXP31_VARIANCES_PER_CASE = {vpc}\n\n"
block += (f"# per-bucket effectiveness re-measured AFTER mechanisms 1+4 were installed\n"
          f"# (the rescale changes materialization rates -- exp23's subtlety), with the\n"
          f"# direction-balance boosts (over {boosts['over']}, under {boosts['under']}) folded into dir_weight\n")
block += f"EXP31_EFFECTIVENESS = {json.dumps(final_eff, indent=1)}\n\n"
block += f"# 97-resolution coins per bucket (phase-2 refit under the mechanisms)\n"
block += f"EXP31_P97_COINS = {p97}\n\n"
block += (f"# direction-aware phase-1 coins per stratum (empirical minus the unit mass,\n"
          f"# renormalized to the residual pool, over per-stratum P(materialize|inject))\n")
block += f"EXP31_PHASE1_COINS = {phase1}\n\n"
block += '''def adopted_dist(dist):
    """Return a dist copy with the exp31 adopted calibration baked in.

    In-memory only -- the committed dist.json/eff.json/inject.json are never
    rewritten. Applies: the re-measured effectiveness (direction-balance
    boosts already folded into dir_weight), the unit-bucket double-counting
    correction (the whole-unit mass already lives in the empirical earned
    mix, so it is subtracted from the earned draw weight first), the refit
    97-resolution coins, and the direction-aware phase-1 coins.
    """
    d = copy.deepcopy(dist)
    d["effectiveness"] = copy.deepcopy(EXP31_EFFECTIVENESS)
    d = apply_unit_bucket_correction(
        d, P_UNIT_DEFAULT, EXP31_VARIANCES_PER_CASE)
    inj = dict(d["injection_rate"])
    inj["p_over_97_resolve"] = dict(EXP31_P97_COINS)
    inj["persistent"] = dict(EXP31_PHASE1_COINS)
    d["injection_rate"] = inj
    return d


def enable_adopted(dist):
    """Install the mechanism patches with the exp31 adopted config and return
    the calibrated dist copy -- the single entry point for the
    --dollar-mechanisms generator default. No separate fitting step: the
    exp26 recalibration is baked in as module defaults (see above).
    Idempotent like enable(); pair with disable() to restore stock behavior.
    """
    enable(under_scale=EXP31_UNDER_SCALE)
    return adopted_dist(dist)
'''

path = ROOT.parent / "src/synth/dollar_mech.py"
text = path.read_text()
assert "exp31: adopted calibration" not in text, "section already present"
assert text.endswith('    return _orig_income is not None\n')
path.write_text(text + "\n\n" + block)
print(f"appended adopted-calibration section to {path}")

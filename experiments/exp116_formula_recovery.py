"""Experiment 116 - black-box formula recovery of the synth benefit calculator.

The recovery side sees ONLY a query oracle: facts in, integer benefit out
(src/synth/benefit.py running in a child process). It never imports
params/benefit. It recovers the calculator's parameters by adaptive
probing (1-D sweeps, kink bisection, integer-sequence fitting), diffs the
recovered table against the auditor's copy of the statute (params.py),
then compiles the recovered formula into network weights and scores it.

Arms:
  A. clean oracle      -> recover, diff vs params (expect exact)
  B. defect oracle     -> stale shelter cap + stale std deduction for
                          size 3 planted via param overrides the recovery
                          cannot see; recover, diff vs params (the diff
                          should name both defects and their dollar size)
  C. compiled weights  -> recovered formula as an MLP (continuous
                          relaxation; the discontinuous finishing steps
                          - final floor, min benefit - applied in code,
                          per the rounding-boundary doctrine), scored
                          against the oracle
  D. trained control   -> sklearn MLP trained on sampler cases, same
                          evals + property probes

Run: python3 experiments/exp116_formula_recovery.py
Writes experiments/exp116_recovery_results.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

ORACLE_SRC = r"""
import json, sys
sys.path.insert(0, {root!r} + "/src")
from synth import benefit, params

overrides = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
for key, val in overrides.items():
    if key == "STANDARD_DEDUCTION":
        for size, v in val.items():
            params.STANDARD_DEDUCTION[int(size)] = v
    else:
        setattr(params, key, val)

for line in sys.stdin:
    req = json.loads(line)
    out = [benefit.compute(f)["benefit"] for f in req["q"]]
    sys.stdout.write(json.dumps({"b": out}) + "\n")
    sys.stdout.flush()
"""


class Oracle:
    """Black-box query access to benefit.compute in a child process."""

    def __init__(self, overrides: dict | None = None):
        src = ORACLE_SRC.replace("{root!r}", repr(str(ROOT)))
        self.proc = subprocess.Popen(
            [sys.executable, "-c", src, json.dumps(overrides or {})],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.n_queries = 0

    def query(self, facts_list: list[dict]) -> list[int]:
        self.proc.stdin.write(json.dumps({"q": facts_list}) + "\n")
        self.proc.stdin.flush()
        resp = json.loads(self.proc.stdout.readline())
        self.n_queries += len(facts_list)
        return resp["b"]

    def close(self):
        self.proc.terminate()


def F(size=3, earned=0.0, unearned=0.0, medical=0.0, senior=False,
      depcare=0.0, shelter=0.0) -> dict:
    return {"hh_size": size, "earned": float(earned), "unearned": float(unearned),
            "medical_exp": float(medical), "senior_disabled": bool(senior),
            "depcare": float(depcare), "shelter": float(shelter)}


def sweep(oracle: Oracle, var: str, values, **base) -> np.ndarray:
    facts = []
    for v in values:
        f = F(**base)
        f[{"earned": "earned", "unearned": "unearned", "medical": "medical_exp",
           "depcare": "depcare", "shelter": "shelter"}[var]] = float(v)
        facts.append(f)
    return np.array(oracle.query(facts), dtype=float)


# ---------------------------------------------------------------- recovery
def recover(oracle: Oracle) -> dict:
    rec: dict = {}

    # 1. Max allotments per size (+ each-additional from sizes 9, 10)
    sizes = list(range(1, 11))
    allot = {s: int(oracle.query([F(size=s)])[0]) for s in sizes}
    rec["max_allotment"] = {s: allot[s] for s in range(1, 9)}
    rec["each_additional_person"] = allot[9] - allot[8]
    assert allot[10] - allot[9] == rec["each_additional_person"]

    # 2. Minimum benefit + which sizes it covers
    floors = {s: int(oracle.query([F(size=s, unearned=20000)])[0]) for s in (1, 2, 3)}
    rec["minimum_benefit"] = floors[1]
    rec["minimum_benefit_sizes"] = [s for s, v in floors.items() if v > 0]

    # 3. Standard deduction per size: first unearned dollar that moves the
    #    benefit below the allotment is std + 1 (the 0.30 rate drops the
    #    floored benefit immediately). Scan to 700 in $1 steps.
    std = {}
    U = np.arange(0, 701)
    for s in range(1, 9):
        b = sweep(oracle, "unearned", U, size=s)
        drop = int(np.argmax(b < allot[s])) if (b < allot[s]).any() else None
        std[s] = drop - 1
    rec["standard_deduction"] = std

    # 4. Benefit rate from the unearned slope (exact: use 1000-dollar span)
    s3 = std[3]
    b0 = oracle.query([F(size=3, unearned=s3 + 100)])[0]
    b1 = oracle.query([F(size=3, unearned=s3 + 1100)])[0]
    rec["benefit_rate"] = (b0 - b1) / 1000.0

    # 5. Earned deduction rate from the long-run earned slope. Then a
    #    structure test: is the deduction floor(rate * E) (a staircase) or
    #    the smooth rate * E? The two differ by < $0.30 of benefit, under
    #    the $1 output floor, but across 3,000 probe points the smooth
    #    model should mismatch hundreds of times if the staircase is real.
    E = np.arange(0, 3001)
    be = sweep(oracle, "earned", E, size=3)
    span = (be[3000] - be[1500]) / 1500.0
    rec["earned_rate"] = 1.0 - (-span) / rec["benefit_rate"]
    allot3 = rec["max_allotment"][3]
    from fractions import Fraction
    rate_frac = Fraction(rec["earned_rate"]).limit_denominator(100)
    rec["earned_rate_fraction"] = f"{rate_frac.numerator}/{rate_frac.denominator}"
    net_smooth = np.maximum(0.0, E - float(rate_frac) * E - s3)
    net_floor = np.maximum(0.0, E - (E * rate_frac.numerator) // rate_frac.denominator - s3)
    pred_smooth = np.floor(allot3 - rec["benefit_rate"] * net_smooth)
    pred_floor = np.floor(allot3 - rec["benefit_rate"] * net_floor)
    rec["earned_model_mismatches"] = {
        "smooth": int((pred_smooth != be).sum()),
        "floored": int((pred_floor != be).sum()),
    }
    rec["earned_deduction_floored"] = bool(
        rec["earned_model_mismatches"]["floored"] == 0
        and rec["earned_model_mismatches"]["smooth"] > 100)

    # 6. Medical threshold (senior): integer-sequence fit over candidates.
    M = np.arange(0, 301)
    bm = sweep(oracle, "medical", M, size=3, unearned=900, senior=True)
    def med_pred(T):
        net = (900 - s3) - np.maximum(0.0, M - T)
        return np.floor(allot3 - rec["benefit_rate"] * np.maximum(net, 0.0))
    fits = [T for T in range(0, 120) if np.array_equal(med_pred(T), bm)]
    rec["medical_threshold"] = fits[0] if len(fits) == 1 else fits
    bm_ns = sweep(oracle, "medical", M, size=3, unearned=900, senior=False)
    rec["medical_conditional_on_senior"] = bool(np.all(bm_ns == bm_ns[0]))

    # 7. Depcare: at size 8 / unearned 2900 the adjusted income stays
    #    positive across the whole sweep, so a 1:1 deduction shows as a
    #    clean +benefit_rate slope and any cap would flatten it early.
    D = np.arange(0, 1501, 10)
    bd = sweep(oracle, "depcare", D, size=8, unearned=2900)
    rec["depcare_slope_per_dollar"] = float((bd[-1] - bd[0]) / 1500.0)
    rec["depcare_uncapped_to"] = 1500 if np.all(np.diff(bd) > 0) else None

    # 8. Shelter: factor from the rising segment (exact sequence fit),
    #    cap from the plateau level (a handful of candidates), absence of
    #    a cap for seniors checked against the uncapped prediction.
    A = 1200 - s3
    S = np.arange(0, 2501)
    bs = sweep(oracle, "shelter", S, size=3, unearned=1200)
    def shelter_pred(f, cap):
        excess = np.maximum(0.0, S - f * A)
        if cap is not None:
            excess = np.minimum(excess, cap)
        net = np.maximum(0.0, A - excess)
        return np.floor(allot3 - rec["benefit_rate"] * net)
    # first index of the final plateau run (excluded from the factor fit:
    #    at that point the cap, if any, has already bound)
    final = bs[-1]
    run = 0
    for v in bs[::-1]:
        if v == final:
            run += 1
        else:
            break
    plat_start = len(bs) - run
    seg = slice(0, plat_start)
    f_found = None
    for f100 in range(30, 71):
        f = f100 / 100.0
        if np.array_equal(shelter_pred(f, None)[seg], bs[seg]):
            f_found = f
            break
    cap_found = None
    if f_found is not None:
        if final >= allot3:
            cap_found = None  # plateau is the net floor itself: no cap seen
        else:
            # Plateau level pins the cap to a ~$3 window (the $1 output
            # floor hides the rest). Disambiguate with confirmation
            # probes at shifted adjusted incomes: a $1 cap difference
            # moves the continuous benefit by $0.30, which crosses an
            # integer boundary for most alignments.
            net_p_hi = (allot3 - final) / rec["benefit_rate"]
            cands = [c for c in range(int(A - net_p_hi) - 2, int(A - net_p_hi) + 6)
                     if c >= 0 and np.array_equal(shelter_pred(f_found, c), bs)]
            for du in (1, 2, 3):
                if len(cands) <= 1:
                    break
                A2 = (1200 - du) - s3
                bs2 = sweep(oracle, "shelter", S, size=3, unearned=1200 - du)
                def pred2(cap, A2=A2, bs2=bs2):
                    excess = np.maximum(0.0, S - f_found * A2)
                    excess = np.minimum(excess, cap)
                    net = np.maximum(0.0, A2 - excess)
                    return np.floor(allot3 - rec["benefit_rate"] * net)
                cands = [c for c in cands if np.array_equal(pred2(c), bs2)]
            cap_found = cands[0] if len(cands) == 1 else cands
    found = (f_found, cap_found) if f_found is not None else None
    rec["shelter_factor"], rec["shelter_cap"] = found if found else (None, None)
    bs_senior = sweep(oracle, "shelter", S, size=3, unearned=1200, senior=True)
    rec["shelter_senior_matches_uncapped"] = bool(
        np.array_equal(shelter_pred(rec["shelter_factor"], None), bs_senior))
    return rec


def statute_truth() -> dict:
    from synth import params
    return {
        "max_allotment": dict(params.MAX_ALLOTMENT),
        "each_additional_person": params.EACH_ADDITIONAL_PERSON,
        "minimum_benefit": params.MINIMUM_BENEFIT,
        "standard_deduction": {s: params.standard_deduction(s) for s in range(1, 9)},
        "benefit_rate": 0.30,
        "earned_rate": params.EARNED_INCOME_DEDUCTION_RATE,
        "medical_threshold": params.MEDICAL_DEDUCTION_THRESHOLD,
        "shelter_factor": 0.5,
        "shelter_cap": params.SHELTER_DEDUCTION_CAP,
    }


def diff_recovery(rec: dict, truth: dict) -> dict:
    out = {}
    for k in ["each_additional_person", "minimum_benefit", "benefit_rate",
              "earned_rate", "medical_threshold", "shelter_factor", "shelter_cap"]:
        out[k] = {"recovered": rec.get(k), "truth": truth[k],
                  "abs_err": (abs(rec[k] - truth[k]) if isinstance(rec.get(k), (int, float)) else None)}
    for table in ["max_allotment", "standard_deduction"]:
        out[table] = {str(s): {"recovered": rec[table][s], "truth": truth[table][s],
                               "abs_err": abs(rec[table][s] - truth[table][s])}
                      for s in range(1, 9)}
    return out


# ---------------------------------------------------------------- compiler
def recovered_benefit_continuous(rec: dict, facts: np.ndarray, size: int) -> np.ndarray:
    """Continuous relaxation of the recovered formula (vectorized).
    facts columns: earned, unearned, medical, depcare, shelter, senior.
    The earned deduction enters as rate * E (the relaxation of the
    staircase); everything else is the recovered structure verbatim.
    """
    E, U, M, D, S, SEN = [facts[:, i] for i in range(6)]
    allot = float(rec["max_allotment"][size])
    std = float(rec["standard_deduction"][size])
    med = SEN * np.maximum(0.0, M - float(rec["medical_threshold"]))
    adjusted = E + U - float(rec["earned_rate"]) * E - std - med - D
    excess = np.maximum(0.0, S - float(rec["shelter_factor"]) * np.maximum(adjusted, 0.0))
    if rec["shelter_cap"] is not None:
        excess = np.where(SEN > 0.5, excess, np.minimum(excess, float(rec["shelter_cap"])))
    net = np.maximum(0.0, adjusted - excess)
    return allot - float(rec["benefit_rate"]) * net


def build_net(rec: dict, size: int) -> dict:
    """Literal weights for the recovered formula as a ReLU network in DAG
    form: a list of units, each {weights: {feature_index: coef}, bias},
    feature indices 0..5 are the inputs [earned, unearned, medical,
    depcare, shelter, senior] and each unit appends one feature.
    Gating gadget: senior * hinge = min(hinge, BIG * senior), with
    min(a, b) = (a + b - relu(a - b) - relu(b - a)) / 2.
    """
    allot = float(rec["max_allotment"][size])
    std = float(rec["standard_deduction"][size])
    rate = float(rec["benefit_rate"])
    erate = float(rec["earned_rate"])
    tmed = float(rec["medical_threshold"])
    f = float(rec["shelter_factor"])
    cap = rec["shelter_cap"]
    BIG = 100000.0
    E_, U_, M_, D_, S_, SEN_ = 0, 1, 2, 3, 4, 5
    units = []

    def add(w: dict, b: float) -> int:
        units.append({"w": {int(k): float(v) for k, v in w.items()}, "b": float(b)})
        return 6 + len(units) - 1  # feature index of this unit's output

    h = add({M_: 1.0}, -tmed)                                # relu(M - tmed)
    a1 = add({h: 1.0, SEN_: -BIG}, 0.0)                      # relu(h - BIG s)
    a2 = add({h: -1.0, SEN_: BIG}, 0.0)                      # relu(BIG s - h)
    med = add({h: 0.5, SEN_: BIG / 2, a1: -0.5, a2: -0.5}, 0.0)  # = min(h, BIG s) >= 0
    adj = add({E_: 1 - erate, U_: 1.0, med: -1.0, D_: -1.0}, -std)  # relu(adjusted)
    exc = add({S_: 1.0, adj: -f}, 0.0)                       # relu(S - f * relu(adj))
    if cap is not None:
        over = add({exc: 1.0}, -float(cap))                  # relu(excess - cap)
        o1 = add({over: 1.0, SEN_: -BIG}, 0.0)
        o2 = add({over: -1.0, SEN_: BIG}, 0.0)
        over_sen = add({over: 0.5, SEN_: BIG / 2, o1: -0.5, o2: -0.5}, 0.0)
        net = add({E_: 1 - erate, U_: 1.0, med: -1.0, D_: -1.0,
                   exc: -1.0, over: 1.0, over_sen: -1.0}, -std)  # relu(adj - capped)
    else:
        net = add({E_: 1 - erate, U_: 1.0, med: -1.0, D_: -1.0, exc: -1.0}, -std)
    return {"units": units, "readout": {net: -rate}, "b_out": allot,
            "inputs": ["earned", "unearned", "medical", "depcare", "shelter", "senior"]}


def net_forward(net: dict, facts: np.ndarray) -> np.ndarray:
    feats = [facts[:, i] for i in range(6)]
    for u in net["units"]:
        val = np.full(facts.shape[0], u["b"])
        for idx, w in u["w"].items():
            val = val + w * feats[int(idx)]
        feats.append(np.maximum(0.0, val))
    out = np.full(facts.shape[0], net["b_out"])
    for idx, w in net["readout"].items():
        out = out + w * feats[int(idx)]
    return out


def finish_benefit(rec: dict, cont: np.ndarray, size: int) -> np.ndarray:
    """Discontinuous finishing steps in ordinary code: the final floor
    and the minimum benefit (order matches benefit.py up to the integer
    equivalence of floor/max for an integer minimum)."""
    out = np.floor(np.maximum(cont, 0.0))
    if size in rec.get("minimum_benefit_sizes", [1, 2]):
        out = np.maximum(out, float(rec["minimum_benefit"]))
    return out


# ---------------------------------------------------------------- eval data
def eval_cases(n_sampler: int, n_uniform: int, seed: int):
    """Sampler households (realistic) + wide-uniform probes (adversarial)."""
    import random
    from synth import household
    rng = random.Random(seed)
    sampler = []
    for _ in range(n_sampler):
        f = household.sample_household(rng)
        sampler.append([f["earned"], f["unearned"], f["medical_exp"],
                        f["depcare"], f["shelter"], 1.0 if f["senior_disabled"] else 0.0,
                        f["hh_size"]])
    rngu = np.random.default_rng(seed)
    uni = np.column_stack([
        rngu.uniform(0, 6000, n_uniform), rngu.uniform(0, 4000, n_uniform),
        rngu.uniform(0, 1500, n_uniform), rngu.uniform(0, 2000, n_uniform),
        rngu.uniform(0, 3000, n_uniform), rngu.integers(0, 2, n_uniform),
        rngu.integers(1, 9, n_uniform)])
    return np.array(sampler, dtype=float), uni


def facts_of(rows: np.ndarray) -> list[dict]:
    return [{"hh_size": int(r[6]), "earned": r[0], "unearned": r[1],
             "medical_exp": r[2], "senior_disabled": bool(r[5]),
             "depcare": r[3], "shelter": r[4]} for r in rows]


# ---------------------------------------------------------------- main
def main():
    results = {}
    truth = statute_truth()

    # Arm A: clean recovery
    oracle = Oracle()
    rec_clean = recover(oracle)
    results["armA_queries"] = oracle.n_queries
    oracle.close()
    results["armA_recovered"] = {k: (dict(v) if isinstance(v, dict) else v)
                                 for k, v in rec_clean.items()}
    results["armA_diff"] = diff_recovery(rec_clean, truth)

    # Arm B: defect recovery (stale cap 638, stale size-3 std 183)
    defect = {"SHELTER_DEDUCTION_CAP": 638, "STANDARD_DEDUCTION": {"3": 183}}
    oracle = Oracle(defect)
    rec_def = recover(oracle)
    results["armB_queries"] = oracle.n_queries
    oracle.close()
    results["armB_diff_vs_statute"] = diff_recovery(rec_def, truth)

    # Evaluation data, scored against the CLEAN oracle
    sampler_rows, uni_rows = eval_cases(20000, 20000, seed=5200)
    oracle = Oracle()
    y_sampler = np.array(oracle.query(facts_of(sampler_rows)), dtype=float)
    y_uni = np.array(oracle.query(facts_of(uni_rows)), dtype=float)
    oracle.close()

    # Arm C: compiled recovered weights, per size. v1 = pure continuous
    # relaxation. v2 = the earned staircase (a discontinuity) computed in
    # code and fed through an input transform: E enters the net only via
    # the (1 - rate) * E combination, so E' = (E - floor(rate * E)) /
    # (1 - rate) makes the net's adjusted income exact.
    def compiled_predict(rec, rows, staircase_in_code=False):
        pred = np.zeros(len(rows))
        num, den = (int(t) for t in rec["earned_rate_fraction"].split("/"))
        for s in range(1, 9):
            m = rows[:, 6] == s
            if not m.any():
                continue
            net = build_net(rec, s)
            X = rows[m][:, :6].copy()
            if staircase_in_code:
                E = X[:, 0]
                X[:, 0] = (E - (E * num) // den) / (1.0 - float(rec["earned_rate"]))
            cont = net_forward(net, X)
            pred[m] = finish_benefit(rec, cont, s)
        return pred

    # net-vs-reference check (the weights encode the recovered formula)
    ref_err = 0.0
    for s in range(1, 9):
        m = uni_rows[:, 6] == s
        if m.any():
            net = build_net(rec_clean, s)
            ref = recovered_benefit_continuous(rec_clean, uni_rows[m][:, :6], s)
            got = net_forward(net, uni_rows[m][:, :6])
            ref_err = max(ref_err, float(np.abs(ref - got).max()))
    results["armC_net_vs_reference_max_err"] = ref_err

    for name, rows, y in [("sampler", sampler_rows, y_sampler), ("uniform", uni_rows, y_uni)]:
        for tag, sic in [("v1_relaxation", False), ("v2_staircase_in_code", True)]:
            p = compiled_predict(rec_clean, rows, staircase_in_code=sic)
            err = np.abs(p - y)
            results[f"armC_{name}_{tag}"] = {
                "exact_agreement": float((err == 0).mean()),
                "max_abs_err": float(err.max()),
                "mean_abs_err": float(err.mean())}

    # Arm D: trained controls on sampler-distribution data, honestly
    # tuned: a scaled MLP (neural control) and a histogram gradient
    # boosting model (this repo's standard probe class).
    from sklearn.neural_network import MLPRegressor
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    rng = np.random.default_rng(52)
    train_rows, _ = eval_cases(40000, 0, seed=777)
    oracle = Oracle()
    y_train = np.array(oracle.query(facts_of(train_rows)), dtype=float)
    oracle.close()
    models = {
        "mlp": make_pipeline(StandardScaler(),
                             MLPRegressor(hidden_layer_sizes=(64, 64),
                                          max_iter=500, early_stopping=True, random_state=52)),
        "gbm": HistGradientBoostingRegressor(max_iter=300, random_state=52),
    }
    for mname, model in models.items():
        model.fit(train_rows, y_train)
        for name, rows, y in [("sampler", sampler_rows, y_sampler), ("uniform", uni_rows, y_uni)]:
            p = model.predict(rows)
            err = np.abs(p - y)
            results[f"armD_{mname}_{name}"] = {
                "max_abs_err": float(err.max()),
                "mean_abs_err": float(err.mean()),
                "pct_within_1": float((err <= 1).mean() * 100)}
        # property probe: benefit must be nonincreasing in unearned income
        mono_viol = 0
        mono_tot = 0
        for _ in range(300):
            r = sampler_rows[rng.integers(0, len(sampler_rows))].copy()
            prev = None
            for u in range(0, 3001, 250):
                r2 = r.copy(); r2[1] = u
                v = float(model.predict(r2.reshape(1, -1))[0])
                if prev is not None and v > prev + 1e-9:
                    mono_viol += 1
                prev = v
                mono_tot += 1
        results[f"armD_{mname}_monotonicity"] = {"violations": mono_viol,
                                                 "checks": mono_tot}

    out = Path(__file__).with_name("exp116_recovery_results.json")
    out.write_text(json.dumps(results, indent=2, default=str))
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()

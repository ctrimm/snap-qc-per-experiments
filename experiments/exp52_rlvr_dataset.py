"""Exp 52 — RLVR (GRPO) training corpus for the QC-variance eval.

Turns synthetic generator cases into exactly the prompt the exp30 eval
(v1.1: few-shot + jargon classification prompt, T1-T5) shows a model, with
the case's ground-truth T1-T5 labels as the verifiable answer. Output is
mlx-lm-lora's GRPODataset shape, the same one the snap-eval RLVR runs used
(public-snap-datasets/experiments/snap-cot-finetune):

  train.jsonl / valid.jsonl -- {"prompt", "answer", "system"}; `prompt` is
      run_lm.build_class_prompt(...) verbatim, `answer` is a JSON string of
      the T1-T5 labels that exp52_rlvr_rewards.py scores completions against.
  manifest.json -- generator settings, counts, label distributions, and the
      field-fidelity notes below.

Recipe (exp43): faithful persistent pool, uniform per-example reward (no
class reweighting). Findings are balanced to thirds by default to match the
eval's sampling frame (exp30 samples correct/over/under ~1:1:1 off the
natural prior); --balance natural keeps the generator's mix.

Field fidelity (synthetic -> eval record). The generator models fewer
fields than the QC file, so some eval fields are derived or absent:
  agency view <- issued_facts run through synth.benefit.compute
  verif view  <- facts run through synth.benefit.compute
  state, rent/util split, SUA codes, homeless, composition, CAT_ELIG,
  child-support fields -> not modeled: "not reported" (or 0 for child
  support, which the generator never draws)
  income by source -> wages (earned) and "other unearned income" (unearned)
  T3-T5 primary variance -> the FIRST variance (synthetic variances carry no
  per-variance dollar amount; the eval uses largest-dollar, which agreed
  with first-recorded on 67.7% of multi-variance test items, exp30 Q2)
These are known train/test gaps, recorded in the manifest.

View-identity calibration. Raw synthetic records leak the label: agency and
verified gross/net/household size match on 100% of synthetic correct cases
and only 3-6% of error cases, vs ~76% / ~48% in real QC records (error
cases often carry reviewer values in the agency fields, or the variance sits
in a field the record doesn't show). --calibrate measures the real rates on
FY2021-2023 public-use files with the eval's denylisted items excluded and
writes aggregate stats only (rates + delta quantiles) to
exp52_view_calibration.json; the builder then (a) perturbs the agency view
of a matching share of correct cases with real-sized deltas and (b) copies
verified values into the agency view of a matching share of error cases.
Training records themselves are all synthetic; no real case is written.

Usage:
  python3 experiments/exp52_rlvr_dataset.py --calibrate
  python3 experiments/exp52_rlvr_dataset.py --n 30000 --train 4000 --valid 200 \\
      --out ../snap-qc-data/derived/exp52_rlvr
"""
import argparse
import json
import random
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "experiments" / "eval_pilot"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(EVAL))
from synth import benefit as benefit_mod  # noqa: E402
from synth.codebook import cause_bucket, element_bucket  # noqa: E402
import labels as L  # noqa: E402
import run_lm  # noqa: E402

FINDING = {1: "correct", 2: "overissuance", 3: "underissuance"}
CALIBRATION = ROOT / "experiments" / "exp52_view_calibration.json"
VIEW_PAIRS = [("raw_gross", "verif_gross"), ("raw_net", "verif_net"),
              ("raw_hhsize", "verif_hhsize")]
QUANTILES = 101


def views_identical(fields):
    return all(fields[a] == fields[b] for a, b in VIEW_PAIRS)


def calibrate():
    """Real P(views identical | finding) and correct-case delta quantiles."""
    import pandas as pd
    import sample as S
    deny = set(Path(EVAL / "denylist.txt").read_text().split()[1::2])
    stats = {f: [0, 0] for f in FINDING.values()}  # [identical, total]
    deltas = {a: [] for a, _ in VIEW_PAIRS}
    for fy in (2021, 2022, 2023):
        df = S.load_year(fy)
        for _, row in df.iterrows():
            r = S.row_dict(row)
            if S.case_id_hash(fy, r.get("STATE"), r.get("YRMONTH"), r.get("HHLDNO")) in deny:
                continue
            status = L._int_or_none(L._num(r, "STATUS"))
            if status not in FINDING:
                continue
            f = L.extract_fields(r)
            if any(f[a] is None or f[b] is None for a, b in VIEW_PAIRS):
                continue
            ident = views_identical(f)
            stats[FINDING[status]][0] += ident
            stats[FINDING[status]][1] += 1
            if FINDING[status] == "correct" and not ident:
                for a, b in VIEW_PAIRS:
                    deltas[a].append(f[a] - f[b])
    q = {}
    for a, xs in deltas.items():
        xs.sort()
        q[a] = [xs[min(len(xs) - 1, int(i * (len(xs) - 1) / (QUANTILES - 1)))]
                for i in range(QUANTILES)]
    out = {"source": "FY2021-2023 QC public-use, eval denylist excluded",
           "p_identical": {k: v[0] / v[1] for k, v in stats.items()},
           "n": {k: v[1] for k, v in stats.items()},
           "correct_delta_quantiles": q}
    CALIBRATION.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("p_identical", "n")}, indent=1))
    print(f"wrote {CALIBRATION}")


def apply_view_calibration(rows, cal, rng):
    """Match real view-identity rates by finding (see module docstring)."""
    synth = {f: [views_identical(fl) for fl, lab in rows if lab["t2"] == f]
             for f in FINDING.values()}
    changed = Counter()
    for fields, lab in rows:
        f = lab["t2"]
        target = cal["p_identical"][f]
        base = sum(synth[f]) / max(1, len(synth[f]))
        ident = views_identical(fields)
        if ident and target < base and rng.random() < (base - target) / base:
            for a, _ in VIEW_PAIRS:  # perturb agency view with real deltas
                fields[a] = max(0, fields[a] + rng.choice(cal["correct_delta_quantiles"][a]))
            if views_identical(fields):  # all-zero draw: force a gross delta
                fields["raw_gross"] += rng.choice([d for d in cal["correct_delta_quantiles"]
                                                   ["raw_gross"] if d] or [1])
            fields["cert_hhsize"] = fields["raw_hhsize"]
            changed["perturbed_" + f] += 1
        elif not ident and target > base and rng.random() < (target - base) / (1 - base):
            for a, b in VIEW_PAIRS:  # agency view carries reviewer values
                fields[a] = fields[b]
            fields["cert_hhsize"] = fields["verif_hhsize"]
            fields["raw_ernded"] = fields["ernd_ded"]
            fields["rep_shel_ded"] = fields["shel_ded"]
            changed["hidden_" + f] += 1
    return dict(changed)


def gen_synth(n, seed, persistent=True):
    # Lineage: exp43 gen_synth (exp25/exp37 protocol).
    tf = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    tf.close()
    cmd = [sys.executable, "-m", "synth.generate", "--n", str(n),
           "--seed", str(seed), "--dist", str(ROOT / "experiments/dist.json"),
           "--max-attempts", "12", "--out", tf.name]
    if not persistent:
        cmd.append("--no-persistent-buckets")
    subprocess.run(cmd, cwd=ROOT / "src", check=True, capture_output=True)
    with open(tf.name) as fh:
        cases = [json.loads(line) for line in fh if line.strip()]
    Path(tf.name).unlink(missing_ok=True)
    return cases


def case_fields(case):
    """Synthetic case -> labels.extract_fields()-shaped dict."""
    f, fi = case["facts"], case["issued_facts"]
    v, a = benefit_mod.compute(f), benefit_mod.compute(fi)
    rnd = lambda x: int(round(x))  # noqa: E731
    inc = []
    if f["earned"] > 0:
        inc.append({"code": "FSWAGES", "label": "wages and salaries",
                    "amount": rnd(f["earned"])})
    if f["unearned"] > 0:
        inc.append({"code": "FSOTHUN", "label": "other unearned income",
                    "amount": rnd(f["unearned"])})
    tot = v["earn_ded"] + v["std_ded"] + v["med_ded"] + f["depcare"] + v["excess_shelter"]
    return {
        "state_name": "", "sample_month": 202400 + int(f.get("review_month", 1)),
        "raw_hhsize": fi["hh_size"], "cert_hhsize": fi["hh_size"],
        "raw_gross": rnd(a["gross"]), "raw_net": rnd(a["net"]),
        "raw_ernded": a["earn_ded"], "rep_csup_ded": 0,
        "rep_depcare_ded": rnd(fi["depcare"]), "rep_med_exp": rnd(fi["medical_exp"]),
        "rep_shel_ded": rnd(a["excess_shelter"]), "rent": None, "util": None,
        "sua_use": None, "sua_amt": None, "homeless": None,
        "verif_unit_size": f["hh_size"], "verif_hhsize": f["hh_size"],
        "verif_gross": rnd(v["gross"]), "verif_net": rnd(v["net"]),
        "verif_earned": rnd(f["earned"]), "verif_unearned": rnd(f["unearned"]),
        "inc_sources": inc, "std_ded": v["std_ded"], "ernd_ded": v["earn_ded"],
        "med_ded": rnd(v["med_ded"]), "shel_ded": rnd(v["excess_shelter"]),
        "tot_ded": rnd(tot), "csup_ded": 0, "shel_exp": rnd(f["shelter"]),
        "homeless_ded": None, "composition": None, "cat_elig": None,
        "has_child": int(f.get("n_kids", 0) > 0),
        "has_elder": int(f.get("n_elderly", 0) > 0),
        "n_elder": f.get("n_elderly", 0), "n_disab": f.get("n_disabled", 0),
        "fsben": case["correct_benefit"],
    }


def case_labels(case):
    """T1-T5 labels with labels.label_case() semantics."""
    finding = FINDING[case["finding"]]
    lab = {"t1": "correct" if finding == "correct" else "error", "t2": finding,
           "t3": None, "t4": None, "t5": None}
    if finding != "correct" and case.get("variances"):
        prim = case["variances"][0]
        lab["t3"] = element_bucket(prim["element"])
        if prim.get("nature") in L.NATURE_SET:
            lab["t4"] = str(prim["nature"])
        lab["t5"] = cause_bucket(prim["cause"]) if prim.get("cause") is not None else "other"
    return lab


LABEL_TARGETS = ROOT / "experiments" / "exp54_label_targets.json"
PRE2024_SHARE = 1000 / 1200  # eval test mix: FY21-23 items vs FY24 items


def label_match(rows, rng, weight_cap=10.0):
    """exp54: make synthetic T3-T5 labels follow the eval's rules.

    1. Fiscal-year coding: tag each case with an era (pre-2024 at the eval's
       5/6 share). Pre-2024 cases follow the FY2021-23 codebook: cause 26
       (no-fault, FY2024-only) is re-drawn from real P(cause | element) and
       natures 56/57 (FY2024-only) are coded 53.
    2. Label mix: per-row weight = product over T3/T4/T5 of real/synthetic
       share (eval definition, largest reportable variance), capped; error
       rows are then drawn by weighted sampling without replacement.
    Returns per-row weights (1.0 for correct cases).
    """
    tg = json.loads(LABEL_TARGETS.read_text())
    cause_pre = tg["cause_given_t3_pre2024"]
    eras = []
    for _, lab in rows:
        era = "pre2024" if rng.random() < PRE2024_SHARE else "fy2024"
        eras.append(era)
        if era == "pre2024" and lab["t3"]:
            if lab["t5"] == "no_fault":
                dist = cause_pre.get(lab["t3"]) or {"agency": 1.0}
                lab["t5"] = rng.choices(list(dist), weights=list(dist.values()))[0]
            if lab["t4"] in ("56", "57"):
                lab["t4"] = "53"
    synth = {(e, t): Counter(lab[t] for (_, lab), ee in zip(rows, eras) if ee == e and lab[t])
             for e in ("pre2024", "fy2024") for t in ("t3", "t4", "t5")}
    w = []
    for (_, lab), e in zip(rows, eras):
        if lab["t1"] == "correct" or not lab["t3"]:
            w.append(1.0)
            continue
        x = 1.0
        for t in ("t3", "t4", "t5"):
            if not lab[t]:
                continue
            c = synth[(e, t)]
            target = tg["marginals"][e][t]
            present = sum(target.get(k, 0) for k in c)  # renormalize over labels synth can produce
            ps = c[lab[t]] / sum(c.values())
            pt = target.get(lab[t], 0) / present if present else 0
            x *= (pt / ps) if ps else 0
        w.append(min(weight_cap, x))
    return w


def weighted_sample(idx, weights, k, rng):
    """Efraimidis-Spirakis weighted sampling without replacement."""
    keys = sorted(((rng.random() ** (1.0 / weights[i]) if weights[i] > 0 else 0.0), i) for i in idx)
    return [i for _, i in keys[-k:]]


def few_shot_examples(items_path):
    # Same deterministic dev examples run_lm.py uses for --condition few.
    dev = [d for d in json.loads(Path(items_path).read_text()) if d["split"] == "dev"]
    seen, examples = set(), []
    for d in dev:
        if d["finding"] not in seen:
            seen.add(d["finding"])
            examples.append((d["fields"], d["labels"]))
        if len(examples) == 3:
            break
    return examples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30000, help="synthetic cases to generate")
    ap.add_argument("--seed", type=int, default=52)
    ap.add_argument("--train", type=int, default=4000)
    ap.add_argument("--valid", type=int, default=200)
    ap.add_argument("--balance", choices=["finding", "errors", "correct", "natural"], default="finding",
                    help="finding: 1/3 each; errors: 20%% correct, 40%% over, 40%% under; "
                         "correct: 50%% correct, 25%% over, 25%% under")
    ap.add_argument("--condition", choices=["few", "zero"], default="few")
    ap.add_argument("--out", default=str(ROOT.parent / "snap-qc-data/derived/exp52_rlvr"))
    ap.add_argument("--calibrate", action="store_true",
                    help="measure real view-identity rates -> exp52_view_calibration.json")
    ap.add_argument("--no-view-calibration", action="store_true")
    ap.add_argument("--label-match", action="store_true",
                    help="exp54: FY-aware coding + reweight T3-T5 toward the eval's real label mix")
    args = ap.parse_args()
    if args.calibrate:
        return calibrate()

    cases = gen_synth(args.n, args.seed)
    rows = [(case_fields(c), case_labels(c)) for c in cases]
    rng = random.Random(args.seed)
    view_changes = None
    if not args.no_view_calibration:
        view_changes = apply_view_calibration(
            rows, json.loads(CALIBRATION.read_text()), rng)
    weights = label_match(rows, rng) if args.label_match else [1.0] * len(rows)
    need = args.train + args.valid
    if args.balance in ("finding", "errors", "correct"):
        by = {f: [i for i, r in enumerate(rows) if r[1]["t2"] == f]
              for f in FINDING.values()}
        share = ({"correct": 1 / 3, "overissuance": 1 / 3, "underissuance": 1 / 3}
                 if args.balance == "finding" else
                 {"correct": 0.2, "overissuance": 0.4, "underissuance": 0.4}
                 if args.balance == "errors" else
                 {"correct": 0.5, "overissuance": 0.25, "underissuance": 0.25})
        want = {f: int(need * share[f]) for f in FINDING.values()}
        short = {f: len(by[f]) for f in FINDING.values() if len(by[f]) < want[f]}
        if short:
            sys.exit(f"not enough cases per finding for {want}: {short}; raise --n")
        idx = []
        for f in FINDING.values():
            idx += weighted_sample(by[f], weights, want[f], rng)
        taken = set(idx)
        idx += rng.sample([i for i in range(len(rows)) if i not in taken], need - len(idx))
        picked = [rows[i] for i in idx]
    else:
        picked = rng.sample(rows, need)
    rng.shuffle(picked)

    examples = few_shot_examples(EVAL / "items.json") if args.condition == "few" else ()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    splits = {"train": picked[:args.train], "valid": picked[args.train:]}
    for name, part in splits.items():
        with open(out / f"{name}.jsonl", "w") as fh:
            for fields, lab in part:
                fh.write(json.dumps({
                    "prompt": run_lm.build_class_prompt(fields, "jargon", examples),
                    "answer": json.dumps(lab),
                    "system": "",
                }) + "\n")

    dist = lambda part, t: dict(Counter(lab[t] for _, lab in part if lab[t])  # noqa: E731
                                .most_common())
    manifest = {
        "experiment": "exp52", "seed": args.seed, "n_generated": len(cases),
        "generator": "persistent pool, --max-attempts 12, experiments/dist.json",
        "balance": args.balance, "condition": f"{args.condition}/jargon",
        "counts": {k: len(v) for k, v in splits.items()},
        "label_match": args.label_match,
        "view_calibration": None if view_changes is None else {
            "file": CALIBRATION.name, "changes_before_sampling": view_changes,
            "p_identical_after": {
                k: {f: sum(views_identical(fl) for fl, lab in v if lab["t2"] == f)
                    / max(1, sum(1 for _, lab in v if lab["t2"] == f))
                    for f in FINDING.values()} for k, v in splits.items()}},
        "label_dist": {k: {t: dist(v, t) for t in ("t2", "t3", "t4", "t5")}
                       for k, v in splits.items()},
        "fidelity_notes": [
            "state, rent/util split, SUA codes, homeless, composition, CAT_ELIG "
            "not modeled -> 'not reported'",
            "child support not modeled -> 0",
            "income by source collapsed to wages + other unearned",
            "T3-T5 primary = first variance (eval uses largest-dollar)",
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: manifest[k] for k in ("n_generated", "counts", "label_dist")},
                     indent=1))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

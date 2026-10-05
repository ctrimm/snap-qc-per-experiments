"""Exp 43 — transformer-class transfer probe (STAGED).

Does the exp25/exp37 transfer recipe (faithful persistent pool +
class-rebalancing during training) hold for a transformer-class model?
Pre-registered decision bar in exp43_transformer_transfer_probe.md.

Two stages:
  --stage data   Regenerate the persistent + retry pools (exp25/exp37
                 protocol) and extract the clean 8-feature set into
                 exp43_pools.npz + exp43_meta.json. Runs in the CPU
                 sandbox. Add --smoke for a fast 2x500-case pipeline check.
  --stage train  Train the tiny feature-tokenizer transformer on the 4
                 arms (pool x loss-weight) x seeds, score on the real
                 FY2024 QC eval split, print the decision bar.
                 Requires torch — staged for the Mac Studio
                 (see exp43_runbook_mac_studio.md). Add --smoke-train for
                 a 1-arm / 1-seed / 2-epoch torch-path check.

Usage:
  python3 experiments/exp43_transformer_transfer_probe.py --stage data [--smoke] [--out DIR]
  python3 experiments/exp43_transformer_transfer_probe.py --stage train --pools DIR [--smoke-train]

Real QC microdata is used for the eval split only — never trained on,
never copied into the repo.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from synth import benefit as benefit_mod  # noqa: E402
from synth import params  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402

QC = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"

# Clean 8-feature set: exp37's v1 minus issued_benefit (PA7 post-decision
# finding; removal was immaterial there, 0.559 vs 0.567 acc).
FEATURES = ["hh_size", "earned", "unearned", "shelter", "sua",
            "medical_exp", "depcare", "senior_disabled"]
BUCKETS = ["earned", "shelter", "unearned", "sua", "medical",
           "hhcomp", "arithmetic", "depcare"]
BUCKET_ID = {b: i for i, b in enumerate(BUCKETS)}
SUA_YES = {"3", "4", "5", "6", "7", "8"}
SEED = 7
N = 20000

# exp37 reference numbers (same eval split) for the probe-validity guard.
REF_LOGREG_UNWEIGHTED_MACROF1 = 0.244


def fnum(v):
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def real_row_features(row):
    # Lineage: experiments/exp37_transfer_model_classes.py; issued_benefit
    # dropped for the clean-8 set (kept out of FEATURES below).
    size = int(fnum(row["CERTHHSZ"]))
    return {
        "hh_size": float(size), "earned": fnum(row["FSEARN"]),
        "unearned": fnum(row["FSUNEARN"]), "shelter": fnum(row["SHELDED"]),
        "sua": 1.0 if row["SUA1"].strip() in SUA_YES else 0.0,
        "medical_exp": fnum(row["FSMEDEXP"]), "depcare": fnum(row["FSDEPDED"]),
        "senior_disabled": 1.0 if (fnum(row["FSNELDER"]) > 0 or fnum(row["FSNDIS"]) > 0) else 0.0,
    }


def synth_case_features(case):
    # Lineage: exp37 (agency-view facts, like the caseworker saw).
    f = case["issued_facts"]
    return {
        "hh_size": float(f["hh_size"]), "earned": f["earned"],
        "unearned": f["unearned"], "shelter": f["shelter"],
        "sua": float(f["sua"]), "medical_exp": f["medical_exp"],
        "depcare": f["depcare"],
        "senior_disabled": float(f["senior_disabled"]),
    }


def load_real():
    import csv
    rows = []
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            status = row["STATUS"].strip()
            e1 = row.get("ELEMENT1", "").strip()
            label = element_bucket(int(e1)) if e1 and status != "1" else None
            if label is None or label not in BUCKET_ID:
                continue
            rows.append(([real_row_features(row)[k] for k in FEATURES],
                         BUCKET_ID[label]))
    return rows


def gen_synth(n, seed, persistent):
    tf = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    path = tf.name
    tf.close()
    cmd = [sys.executable, "-m", "synth.generate", "--n", str(n),
           "--seed", str(seed), "--dist", str(ROOT / "experiments/dist.json"),
           "--max-attempts", "12", "--out", path]
    if not persistent:
        cmd.append("--no-persistent-buckets")
    subprocess.run(cmd, cwd=ROOT / "src", check=True, capture_output=True)
    return path


def synth_rows(path):
    import json as js
    rows = []
    with open(path) as fh:
        for line in fh:
            c = js.loads(line)
            if not c.get("variances"):
                continue
            b = c["variances"][0]["element_bucket"]
            if b not in BUCKET_ID:
                continue
            rows.append(([synth_case_features(c)[k] for k in FEATURES],
                         BUCKET_ID[b]))
    return rows


def stage_data(out_dir, smoke=False):
    n = 500 if smoke else N
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pools = {}
    for name, persistent in (("persistent", True), ("retry", False)):
        print(f"[data] generating {name} pool (n={n}) ...", flush=True)
        path = gen_synth(n, SEED, persistent)
        rows = synth_rows(path)
        Path(path).unlink(missing_ok=True)
        X = np.array([r[0] for r in rows], dtype=np.float64)
        y = np.array([r[1] for r in rows], dtype=np.int64)
        pools[name] = (X, y)
        print(f"[data] {name}: {len(y)} error rows; "
              f"class counts {dict(sorted(Counter(y.tolist()).items()))}", flush=True)
    # Standardize on the persistent pool's training rows only.
    mu = pools["persistent"][0].mean(axis=0)
    sd = pools["persistent"][0].std(axis=0)
    sd[sd == 0] = 1.0
    data = {"feature_names": np.array(FEATURES), "bucket_names": np.array(BUCKETS),
            "mu": mu, "sd": sd}
    for name, (X, y) in pools.items():
        data[f"X_{name}"] = (X - mu) / sd
        data[f"y_{name}"] = y
    test = load_real()
    data["X_test"] = (np.array([r[0] for r in test]) - mu) / sd
    data["y_test"] = np.array([r[1] for r in test])
    np.savez_compressed(out / "exp43_pools.npz", **data)
    meta = {"n_requested": n, "seed": SEED, "max_attempts": 12,
            "features": FEATURES, "buckets": BUCKETS,
            "n_persistent": int(len(pools["persistent"][1])),
            "n_retry": int(len(pools["retry"][1])),
            "n_test": int(len(test)),
            "note": "standardization fit on persistent train rows only"}
    (out / "exp43_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[data] wrote {out / 'exp43_pools.npz'} "
          f"(test rows: {len(test)})", flush=True)


# ---------------------------------------------------------------- Stage 2
def stage_train(pools_dir, seeds, smoke_train=False):
    try:
        import torch
        import torch.nn as nn
    except ImportError:
        sys.exit("torch is not installed here. Stage 2 is staged for the "
                 "Mac Studio — see experiments/exp43_runbook_mac_studio.md")
    from sklearn.metrics import accuracy_score, f1_score

    d = np.load(Path(pools_dir) / "exp43_pools.npz")
    Xp, yp = d["X_persistent"].astype(np.float32), d["y_persistent"].astype(np.int64)
    Xr, yr = d["X_retry"].astype(np.float32), d["y_retry"].astype(np.int64)
    Xt, yt = d["X_test"].astype(np.float32), d["y_test"].astype(np.int64)
    n_feat, n_cls = Xp.shape[1], len(BUCKETS)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"[train] device={device}, features={n_feat}, classes={n_cls}")

    class FeatureTokenizer(nn.Module):
        def __init__(self, n_features, d_model):
            super().__init__()
            self.proj = nn.ModuleList([nn.Linear(1, d_model)
                                       for _ in range(n_features)])

        def forward(self, x):  # (B, F) -> (B, F, D)
            return torch.stack([lin(x[:, i:i + 1])
                                for i, lin in enumerate(self.proj)], dim=1)

    class TinyTabTransformer(nn.Module):
        def __init__(self, d_model=64, n_layers=2, n_heads=4,
                     ffn_dim=128, dropout=0.1):
            super().__init__()
            self.tokenizer = FeatureTokenizer(n_feat, d_model)
            self.cls = nn.Parameter(torch.randn(1, 1, d_model) * 0.02)
            layer = nn.TransformerEncoderLayer(
                d_model=d_model, nhead=n_heads, dim_feedforward=ffn_dim,
                dropout=dropout, batch_first=True, norm_first=True)
            self.encoder = nn.TransformerEncoder(layer, num_layers=n_layers)
            self.norm = nn.LayerNorm(d_model)
            self.head = nn.Linear(d_model, n_cls)

        def forward(self, x):
            tok = self.tokenizer(x)
            cls = self.cls.expand(x.size(0), -1, -1)
            h = self.encoder(torch.cat([cls, tok], dim=1))
            return self.head(self.norm(h[:, 0]))

    def stratified_split(X, y, frac=0.1, seed=0):
        rng = np.random.default_rng(seed)
        val_idx = []
        for c in np.unique(y):
            idx = np.where(y == c)[0]
            rng.shuffle(idx)
            val_idx.extend(idx[:max(1, int(len(idx) * frac))].tolist())
        mask = np.ones(len(y), dtype=bool)
        mask[val_idx] = False
        return (X[mask], y[mask]), (X[val_idx], y[val_idx])

    def run_arm(X, y, weighted, seed):
        torch.manual_seed(seed)
        np.random.seed(seed)
        (Xtr, ytr), (Xva, yva) = stratified_split(X, y, seed=seed)
        tr = torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(
                torch.from_numpy(Xtr), torch.from_numpy(ytr)),
            batch_size=256, shuffle=True,
            generator=torch.Generator().manual_seed(seed))
        va_X = torch.from_numpy(Xva).to(device)
        va_y = torch.from_numpy(yva).to(device)
        te_X = torch.from_numpy(Xt).to(device)

        model = TinyTabTransformer().to(device)
        n, K = len(ytr), n_cls
        cnt = Counter(ytr.tolist())
        w = torch.tensor([n / (K * cnt[c]) for c in range(K)],
                         dtype=torch.float32).to(device) if weighted else None
        crit = nn.CrossEntropyLoss(weight=w)
        opt = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=1e-4)
        sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt, mode="max", factor=0.5, patience=5)

        epochs = 2 if smoke_train else 80
        best_f1, best_state, bad = -1.0, None, 0
        for ep in range(epochs):
            model.train()
            for xb, yb in tr:
                xb, yb = xb.to(device), yb.to(device)
                opt.zero_grad()
                crit(model(xb), yb).backward()
                opt.step()
            model.eval()
            with torch.no_grad():
                pred = model(va_X).argmax(1).cpu().numpy()
            f1 = f1_score(yva, pred, average="macro", zero_division=0)
            sched.step(f1)
            if f1 > best_f1 + 1e-4:
                best_f1, bad = f1, 0
                best_state = {k: v.cpu().clone()
                              for k, v in model.state_dict().items()}
            else:
                bad += 1
                if bad >= 15 and not smoke_train:
                    break
        model.load_state_dict({k: v.to(device)
                               for k, v in best_state.items()})
        model.eval()
        with torch.no_grad():
            pred = model(te_X).argmax(1).cpu().numpy()
        return accuracy_score(yt, pred), f1_score(yt, pred, average="macro",
                                                 zero_division=0)

    arms = [("t1", Xp, yp, False, "persistent/uniform"),
            ("t2", Xr, yr, False, "retry/uniform"),
            ("t3", Xp, yp, True, "persistent/balanced-loss"),
            ("t4", Xr, yr, True, "retry/balanced-loss")]
    if smoke_train:
        arms, seeds = arms[:1], seeds[:1]
    results = {}
    for key, X, y, weighted, label in arms:
        accs, f1s = [], []
        for s in seeds:
            a, f = run_arm(X, y, weighted, s)
            accs.append(a)
            f1s.append(f)
            print(f"[train] {label} seed={s}: acc={a:.3f} macroF1={f:.3f}",
                  flush=True)
        results[key] = (float(np.mean(accs)), float(np.mean(f1s)),
                        float(np.ptp(f1s)))
        print(f"[train] {label}: acc={np.mean(accs):.3f} "
              f"macroF1={np.mean(f1s):.3f} (range {np.ptp(f1s):.3f})", flush=True)

    if smoke_train:
        print("[train] smoke-train OK — torch path works; run the full "
              "battery per the runbook.")
        return

    def m(key):
        return results[key][1]

    print("\n=== DECISION BAR (pre-registered) ===")
    guard = m("t1") > REF_LOGREG_UNWEIGHTED_MACROF1 \
        or m("t3") > REF_LOGREG_UNWEIGHTED_MACROF1
    print(f"1. probe-validity guard (best arm macroF1 > "
          f"{REF_LOGREG_UNWEIGHTED_MACROF1:.3f}, exp37 logreg-unweighted): "
          f"{'PASS' if guard else 'FAIL — do not interpret; revisit tuning'}")
    pool = m("t1") >= m("t2") - 0.01
    print(f"2. pool question (persistent/uniform {m('t1'):.3f} vs "
          f"retry/uniform {m('t2'):.3f}): "
          f"{'PASS — lock persistent pool for LM recipe' if pool else 'FAIL — re-derive pool choice'}")
    w = m("t3") - m("t1")
    if w < -0.02:
        wv = ("FAIL — balanced loss does NOT port (logreg failure repeated); "
              "LM recipe uses uniform loss")
    elif w >= -0.01:
        wv = "PASS — reweighting safe to port"
    else:
        wv = "MARGINAL — judgment call; consider the resampling follow-up"
    print(f"3. reweighting question (balanced {m('t3'):.3f} vs uniform "
          f"{m('t1'):.3f}, Δ={w:+.3f}): {wv}")
    if guard and pool and w >= -0.01:
        print("OVERALL: full recipe ports to transformer-class.")
    else:
        print("OVERALL: at least one component needs re-derivation — see above.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["data", "train"], required=True)
    ap.add_argument("--out", default="/tmp/exp43",
                    help="output dir for --stage data")
    ap.add_argument("--pools", default="/tmp/exp43",
                    help="dir holding exp43_pools.npz for --stage train")
    ap.add_argument("--smoke", action="store_true",
                    help="stage data: 2x500-case pipeline check")
    ap.add_argument("--smoke-train", action="store_true",
                    help="stage train: 1 arm / 1 seed / 2 epochs")
    ap.add_argument("--seeds", default="7,8,9",
                    help="comma-separated torch seeds for --stage train")
    args = ap.parse_args()
    if args.stage == "data":
        stage_data(args.out, smoke=args.smoke)
    else:
        stage_train(args.pools, [int(s) for s in args.seeds.split(",")],
                    smoke_train=args.smoke_train)


if __name__ == "__main__":
    main()

"""Exp104 part D: a learned router (5-fold cross-validated logistic regression), from existing runs + exp104 signals.

Features (all available when answering a question): topic labels (31B, E4B: noncitizens / self-employment / income /
deduction groups), the plain agent's answer differs from the 31B no-tool majority / from E4B's no-tool majority,
31B and E4B 5-sample agreement, plain-agent tool calls. Target: the plain agent is wrong. Policy: escalate a question
when P(wrong) > t to a target setup (date+notes or combined); t picked inside each training fold. Accuracy is pooled
over the held-out folds. Exploratory (evaluation set).
"""
import collections
import csv
import glob
import random
import sys
from pathlib import Path

import numpy as np
from inspect_ai.log import read_eval_log


class LogisticRegression:
    """Minimal L2-regularized logistic regression (gradient descent on standardized features; numpy only)."""

    def __init__(self, max_iter=2000, C=1.0):
        self.it, self.lam = max_iter, 1.0 / C

    def fit(self, X, y):
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        Z = (X - self.mu) / self.sd
        self.w, self.b = np.zeros(Z.shape[1]), 0.0
        for _ in range(self.it):
            p = 1 / (1 + np.exp(-(Z @ self.w + self.b)))
            g = Z.T @ (p - y) / len(y) + self.lam * self.w / len(y)
            self.w -= 0.5 * g; self.b -= 0.5 * float(np.mean(p - y))
        self.coef_ = [self.w]
        return self

    def predict_proba(self, X):
        p = 1 / (1 + np.exp(-(((X - self.mu) / self.sd) @ self.w + self.b)))
        return np.stack([1 - p, p], axis=1)


def roc_auc_score(y, p):
    pos, neg = p[y == 1], p[y == 0]
    return float(np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg]))

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exp94_96_analyze as A  # noqa: E402

ROWS = {r["question_id"]: r for r in csv.DictReader(open(A.CORNELL, encoding="utf-8-sig"))}
IDS = sorted(ROWS, key=int)
KEY = {i: ROWS[i]["correct_single_answer"].strip() for i in IDS}


def full(d):
    l = read_eval_log(sorted(glob.glob(str(A.D / d / "*.eval")))[-1])
    out = {}
    for s in l.samples:
        sc = list(s.scores.values())[0] if s.scores else None
        calls = sum(1 for m in s.messages if m.role == "assistant" for tc in (m.tool_calls or []) if tc.function != "submit")
        out[str(s.id)] = (sc.answer if sc else None, calls)
    return out


def sig(d):
    out = collections.defaultdict(list)
    for s in read_eval_log(sorted(glob.glob(str(A.D / "exp104_logs" / d / "*.eval")))[-1]).samples:
        out[str(s.id)].append(list(s.scores.values())[0].answer if s.scores else None)
    return out


def main():
    P, D, C = full("exp98_logs/31b_agent_2026"), full("exp102_logs/full_plain_date_notes"), full("exp98_logs/31b_combo_think_verify")
    s31, s4, t31, t4 = sig("31b_sc5"), sig("e4b_sc5"), sig("31b_topic"), sig("e4b_topic")
    groups = {"noncit": ("noncitizen",), "selfemp": ("self-employment",), "income": ("income", "earned", "unearned"),
              "deduct": ("deduction", "shelter", "utility", "medical", "dependent", "child-support")}

    def feats(i):
        m31 = collections.Counter(s31[i]).most_common(1)[0]; m4 = collections.Counter(s4[i]).most_common(1)[0]
        f = [float(P[i][0] != m31[0]), float(P[i][0] != m4[0]), m31[1] / 5, m4[1] / 5, min(P[i][1], 10) / 10]
        for tl in (t31[i][0] or "", t4[i][0] or ""):
            f += [float(any(k in tl for k in ks)) for ks in groups.values()]
        return f
    X = np.array([feats(i) for i in IDS]); y = np.array([float(P[i][0] != KEY[i]) for i in IDS])
    rng = random.Random(104); order = IDS[:]; rng.shuffle(order); folds = [order[k::5] for k in range(5)]
    idx = {i: n for n, i in enumerate(IDS)}
    for tname, T in (("date+notes", D), ("combined", C)):
        right = esc = 0
        for k in range(5):
            test = folds[k]; train = [i for i in IDS if i not in set(test)]
            clf = LogisticRegression(max_iter=1000, C=1.0).fit(X[[idx[i] for i in train]], y[[idx[i] for i in train]])
            ptr = clf.predict_proba(X[[idx[i] for i in train]])[:, 1]
            best, bt = -1, 1.0
            for t in sorted(set(np.round(ptr, 3))) + [1.0]:
                a = sum((T[i][0] if p > t else P[i][0]) == KEY[i] for i, p in zip(train, ptr))
                if a > best:
                    best, bt = a, t
            pte = clf.predict_proba(X[[idx[i] for i in test]])[:, 1]
            right += sum((T[i][0] if p > bt else P[i][0]) == KEY[i] for i, p in zip(test, pte))
            esc += int(sum(pte > bt))
        print(f"learned router -> {tname}: {100 * right / 500:.1f}% (plain 89.6%); escalated {100 * esc / 500:.1f}%")
    clf = LogisticRegression(max_iter=1000).fit(X, y)
    names = ["plain≠31B no-tool", "plain≠E4B no-tool", "31B agreement", "E4B agreement", "tool calls"] + \
            [f"{m} topic {g}" for m in ("31B", "E4B") for g in groups]
    pcv = np.zeros(len(IDS))
    for k in range(5):
        te = [idx[i] for i in folds[k]]; tr = [n for n in range(len(IDS)) if n not in set(te)]
        pcv[te] = LogisticRegression().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    print("cross-validated AUROC for plain-agent errors:", round(roc_auc_score(y, pcv), 3))
    print("coefficients:", ", ".join(f"{n} {c:+.2f}" for n, c in sorted(zip(names, clf.coef_[0]), key=lambda x: -abs(x[1]))[:6]))


if __name__ == "__main__":
    main()

"""Exp 88 — do rule excerpts make flag-card notes cite the right rule without misstating it?

Pre-registered (this docstring, committed before the scored runs):
  Data: the 327 v2 flag cards in exp76_cards.jsonl (PA and NY QC cases, 2020-2024).
  Rules: each "check first" element maps to its governing federal rule (ELEMENT_RULES); the excerpt is
  that citation's text from state-policy-docs (get_section), as of July 1 of the case year or
  2024-01-01, whichever is later (the corpus holds CFR versions from 2024 on), trimmed to 900
  characters.
  Writer: google/gemma-4-e4b via LM Studio (stock weights), temperature 0, max 220 tokens.
    plain     exp62's note prompt (card only, at most 70 words)
    grounded  the same prompt plus the excerpts, at most 90 words, and: after each check, give the
              rule's citation in parentheses exactly as written above the excerpt; state a rule only
              if the excerpt says it
  Judge: google/gemma-4-31b, temperature 0, sees the excerpts and one note, and lists every statement
  about what a rule requires or allows with supported / unsupported / contradicted. Same excerpts for
  both arms, so a plain note's rule claims are checked too.
  Readouts (per arm): citation coverage (checked elements with a mapped rule whose citation appears);
  unsupplied citations (CFR/U.S.C./MPP citations not given in the prompt); notes failing exp62's faithfulness check
  (numbers/topics not on the card, blame words) and its other frozen checks; words; judge counts (rule claims per note; share unsupported or
  contradicted). Paired bootstrap 95% CIs (2,000 resamples, seed 88) for grounded - plain.
  Hypotheses: H1 grounded notes cite the governing rule for most checked elements (coverage > 80%)
  with few unsupplied citations (< 5% of notes). H2 grounded notes' rule claims are mostly supported
  (unsupported or contradicted < 10%). H3 grounding does not raise the share of notes with numbers
  not on the card (difference CI includes 0 or is negative).

Usage: python experiments/exp88_grounded_notes.py write --arm plain|grounded
       python experiments/exp88_grounded_notes.py judge --arm plain|grounded
       python experiments/exp88_grounded_notes.py score
"""
import argparse
import json
import os
import random
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPD = Path(os.environ.get("EXP88_SPD", HERE.parents[1] / "state-policy-docs"))
OUT = HERE.parents[1] / "snap-qc-data" / "derived" / "exp88"
API = os.environ.get("OPENAI_BASE_URL", "http://localhost:1234/v1")
sys.path.insert(0, str(HERE))
_argv = sys.argv; sys.argv = sys.argv[:1]
import exp62_check as K  # noqa: E402
import exp62_rewrite as R  # noqa: E402
sys.argv = _argv
R.WORDING = "v2"
PROMPT = R.PROMPT

ELEMENT_RULES = {
    "shelter": "7 CFR 273.9(d)(6)(ii)", "unearned": "7 CFR 273.9(b)(2)", "earned": "7 CFR 273.9(b)(1)",
    "sua": "7 CFR 273.9(d)(6)(iii)", "medical": "7 CFR 273.9(d)(3)", "hhcomp": "7 CFR 273.1(a)",
    "depcare": "7 CFR 273.9(d)(4)", "childsupport": "7 CFR 273.9(d)(5)", "arithmetic": "7 CFR 273.10(e)(1)",
}
GROUNDED_EXTRA = """

Rules for the parts to check (official text, trimmed):
{rules}

Changes for this note: at most 90 words. After each part you tell the caseworker to check, give that rule's citation in parentheses exactly as written above (for example "(7 CFR 273.9(d)(6)(ii))"). State what a rule requires only if the excerpt above says it."""
JUDGE = """You check notes written for SNAP caseworkers against official rule text.

Rule excerpts:
{rules}

Note:
{note}

List every statement in the note about what a SNAP rule requires, allows, counts or deducts (not instructions like "check X" or "ask for Y", and not facts about this case). For each, say whether the excerpts support it. Answer with JSON only: {{"claims": [{{"text": "...", "verdict": "supported" | "unsupported" | "contradicted"}}]}}. If there are no such statements, answer {{"claims": []}}."""


def chat(model, prompt, max_tokens):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0,
                       "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(f"{API}/chat/completions", data=body, headers={"Content-Type": "application/json",
                                                                               "Authorization": "Bearer lm-studio"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]["content"].strip()


def cards():
    return [json.loads(l) for l in open(HERE / "exp76_cards.jsonl")]


def card_text(c):
    return R.card_text(c)  # the v2 card wording (as exp77)


def excerpts(c):
    sys.path.insert(0, str(SPD))
    os.environ.setdefault("STATE_POLICY_CORPUS", str(SPD / "corpus"))
    from mcp_server.policy_index import get_index, resolve_citation
    year = int(c["card_id"].split("-")[-2])
    as_of = max(date(year, 7, 1), date(2024, 1, 1))
    out = []
    for x in c["check_first"]:
        cite = ELEMENT_RULES.get(x["part"])
        if not cite:
            continue
        r = resolve_citation(get_index(), cite, as_of)
        if "error" in r:
            continue
        text = " ".join(r["text"].split())[:900]
        out.append((x["part"], cite, text))
    return out


def rules_block(ex):
    return "\n\n".join(f"{cite} ({part}): {text}" for part, cite, text in ex)


def write(arm):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"notes_{arm}.jsonl"
    done = {json.loads(l)["card_id"] for l in open(path)} if path.exists() else set()
    with open(path, "a") as fh:
        for c in cards():
            if c["card_id"] in done:
                continue
            ex = excerpts(c)
            prompt = PROMPT.format(card=card_text(c))
            if arm == "grounded":
                prompt = prompt.replace("\n\nNote:", GROUNDED_EXTRA.format(rules=rules_block(ex)) + "\n\nNote:")
            note = chat("google/gemma-4-e4b", prompt, 220)
            fh.write(json.dumps({"card_id": c["card_id"], "note": note, "cites": [e[1] for e in ex]}) + "\n"); fh.flush()


def judge(arm):
    cmap = {c["card_id"]: c for c in cards()}
    src, path = OUT / f"notes_{arm}.jsonl", OUT / f"judge_{arm}.jsonl"
    done = {json.loads(l)["card_id"] for l in open(path)} if path.exists() else set()
    with open(path, "a") as fh:
        for l in open(src):
            n = json.loads(l)
            if n["card_id"] in done:
                continue
            raw = chat("google/gemma-4-31b", JUDGE.format(rules=rules_block(excerpts(cmap[n["card_id"]])), note=n["note"]), 800)
            m = re.search(r"\{.*\}", raw, re.S)
            try:
                claims = json.loads(m.group(0))["claims"] if m else None
            except (json.JSONDecodeError, KeyError):
                claims = None
            fh.write(json.dumps({"card_id": n["card_id"], "claims": claims, "raw": None if claims is not None else raw}) + "\n"); fh.flush()


CITE_RE = re.compile(r"\d+\s*CFR\s*[\d.]+(?:\([A-Za-z0-9]+\))*|7\s*U\.?S\.?C\.?\s*\d+[a-z]?(?:\([A-Za-z0-9]+\))*|MPP\s*63-[\d.]+", re.I)


def norm(c):
    return re.sub(r"\s+", " ", c.upper().replace("§", "")).strip()


def note_metrics(n, card, arm):
    note = n["note"]
    given = {norm(c) for c in n["cites"]}
    found = {norm(c) for c in CITE_RE.findall(note)}
    covered = sum(1 for c in given if any(f.startswith(c) or c.startswith(f) for f in found)) / len(given) if given else None
    unsupplied = any(not any(f.startswith(g) or g.startswith(f) for g in given) for f in found)
    # exp62's frozen checks (numbers and topics not on the card, forbidden blame words, order, length,
    # reading grade), on the note with its citations removed
    K.MAX_WORDS = 90 if arm == "grounded" else 70
    chk = K.check(card, re.sub(r"\(\s*" + CITE_RE.pattern + r"\s*\)", "", note, flags=re.I))
    return {"coverage": covered, "unsupplied": unsupplied, "extra_number": not chk["faithful"],
            "leads": chk["leads"], "pass": chk["pass"], "words": len(note.split())}


def score():
    cmap = {c["card_id"]: c for c in cards()}
    res = {}
    for arm in ("plain", "grounded"):
        p = OUT / f"notes_{arm}.jsonl"
        if not p.exists():
            continue
        notes = {json.loads(l)["card_id"]: json.loads(l) for l in open(p)}
        m = {k: note_metrics(n, cmap[k], arm) for k, n in notes.items()}
        jp = OUT / f"judge_{arm}.jsonl"
        j = {json.loads(l)["card_id"]: json.loads(l)["claims"] for l in open(jp)} if jp.exists() else {}
        res[arm] = {"m": m, "j": j}
    out = {}
    for arm, d in res.items():
        m, j = d["m"], d["j"]
        cov = [v["coverage"] for v in m.values() if v["coverage"] is not None]
        claims = [c for v in j.values() if v for c in v]
        out[arm] = {"notes": len(m), "citation_coverage": round(sum(cov) / len(cov), 3) if cov else None,
                    "notes_with_unsupplied_citation": round(sum(v["unsupplied"] for v in m.values()) / len(m), 3),
                    "notes_not_faithful_to_card": round(sum(v["extra_number"] for v in m.values()) / len(m), 3),
                    "notes_leading_with_first_check": round(sum(v["leads"] for v in m.values()) / len(m), 3),
                    "notes_passing_exp62_checks": round(sum(v["pass"] for v in m.values()) / len(m), 3),
                    "mean_words": round(sum(v["words"] for v in m.values()) / len(m), 1),
                    "judged_notes": len(j), "unparsed_judgments": sum(1 for v in j.values() if v is None),
                    "rule_claims_per_note": round(len(claims) / max(1, len([v for v in j.values() if v is not None])), 2),
                    "claims_unsupported_or_contradicted": round(sum(c.get("verdict") != "supported" for c in claims) / len(claims), 3) if claims else None}
    if "plain" in res and "grounded" in res:
        ids = sorted(set(res["plain"]["m"]) & set(res["grounded"]["m"]))
        d = [int(res["grounded"]["m"][i]["extra_number"]) - int(res["plain"]["m"][i]["extra_number"]) for i in ids]
        rng = random.Random(88)
        boots = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(2000))
        out["extra_number_grounded_minus_plain"] = [round(sum(d) / len(d), 3), round(boots[50], 3), round(boots[1949], 3)]
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["write", "judge", "score"])
    ap.add_argument("--arm", default="plain")
    a = ap.parse_args()
    {"write": lambda: write(a.arm), "judge": lambda: judge(a.arm), "score": score}[a.cmd]()

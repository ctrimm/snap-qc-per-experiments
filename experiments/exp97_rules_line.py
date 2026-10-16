"""Exp97 — the flag-card "Rules:" line, appended by code and filtered to the parts the note names, on fresh cards.

Pre-registered (this docstring and exp97_rules_line.md, committed before the scored runs):
  Cards: exp97_cards.jsonl, 517 v2 cards (three parts, calibrated odds) for the ID, UT and SD holdout cases
  (exp62_flag_cards.py --states ID,UT,SD --top-k 3 --calibrate --wording v2). No note has been written for these
  cases before (the exp76/77 training cards are cross-fitted on the non-holdout rows; overlap 0).
  Writers (mlx, greedy, exp62_rewrite.py v2 wording):
    e2b   the shipped note model: exp77's E2B (gemma-4-e2b-it-bf16 + exp77 LoRA, step 500)
    e4b   gemma-4-e4b-it-bf16 zero-shot (exp88/89's plain arm used the Q4 build in LM Studio)
  Rules line (code, never the model): for each of the card's check parts with a governing rule (ELEMENT_RULES,
  exp88's fixed map), the citation resolved as of max(July 1 of the case year, 2024-01-01). Two versions:
    all       every mapped check part: "Rules for the parts to check: earned income: 7 CFR 273.9(b)(1); ..."
    filtered  only the parts the note names (keyword detector NAMED below); if it finds none, the "all" line
  Reference for which parts a note names: Gemma 4 31B (LM Studio, temperature 0) reads the note and the card's part
  names and lists the parts the note tells the caseworker to check or ask about.
  Readouts per writer: exp76's checks on the note prose (pass all, keeps odds and benefit, words, grade); for the
  filtered line, precision and recall of the listed parts against the 31B reference (micro over notes) and the
  share of notes where it matches exactly; the same precision for the "all" line; share of notes where the detector
  found nothing; share of citations that resolve in the corpus on the case date.
  Hypotheses: H1 the E2B notes pass all checks on at least 90% of the fresh cards (exp77: 94% on PA/NY).
  H2 the filtered line's precision and recall are each at least 95% for both writers. H3 (descriptive) the
  "all" line's precision, i.e. how often an unfiltered line cites a part the note never mentions.
Usage: python experiments/exp97_rules_line.py judge WRITER | score
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPD = Path(os.environ.get("EXP87_SPD", HERE.parents[1] / "state-policy-docs"))
OUT = HERE.parents[1] / "snap-qc-data" / "derived" / "exp97"
API = os.environ.get("OPENAI_BASE_URL", "http://localhost:1234/v1")
sys.path.insert(0, str(HERE))
_argv = sys.argv; sys.argv = sys.argv[:1]
import exp76_check as C  # noqa: E402  (exp62's frozen checks, 80-word limit, keeps_odds)
sys.argv = _argv

ELEMENT_RULES = {  # exp88's fixed map
    "shelter": "7 CFR 273.9(d)(6)(ii)", "unearned": "7 CFR 273.9(b)(2)", "earned": "7 CFR 273.9(b)(1)",
    "sua": "7 CFR 273.9(d)(6)(iii)", "medical": "7 CFR 273.9(d)(3)", "hhcomp": "7 CFR 273.1(a)",
    "depcare": "7 CFR 273.9(d)(4)", "childsupport": "7 CFR 273.9(d)(5)", "arithmetic": "7 CFR 273.10(e)(1)",
}
NAMED = {  # what counts as the note naming a part
    "earned": r"earned income|earnings|wages|pay ?stubs?|paychecks?|\bjob\b|\bwork hours\b|\bhours\b",
    "unearned": r"unearned|social security|\bssi\b|unemployment|award letters?|data match",
    "shelter": r"shelter|\brent\b|lease|mortgage|housing cost",
    "sua": r"utilit|heating|cooling",
    "medical": r"medical",
    "depcare": r"dependent care|child ?care|care provider",
    "hhcomp": r"household size|household members?|who lives|moved (in|out)|lives in the home|living in the home",
    "childsupport": r"child support (paid|payments?)|court orders?",
    "arithmetic": r"benefit math|calculation|\bmath\b|totals|amounts? entered",
}
JUDGE = """A note for a SNAP caseworker is below, followed by the parts of the case its flag card says to check.

Note:
{note}

Parts on the card: {parts}

Which of these parts does the note tell the caseworker to check or ask about (by name or by what to ask for)? Use the part names exactly as listed. Answer with JSON only: {{"parts": ["..."]}}."""


def cards():
    return {c["card_id"]: c for c in map(json.loads, open(HERE / "exp97_cards.jsonl"))}


def as_of(card_id):
    return max(date(int(card_id.split("-")[-2]), 7, 1), date(2024, 1, 1))


def named_parts(card, note):
    t = note.lower()
    return [x["part"] for x in card["check_first"] if x["part"] in NAMED and re.search(NAMED[x["part"]], t)]


def rules_line(card, note=None, resolve=None):
    """The line the pipeline appends. note=None gives the unfiltered line."""
    parts = [x for x in card["check_first"] if x["part"] in ELEMENT_RULES]
    label = "Rules for the parts to check"
    if note is not None:
        keep = set(named_parts(card, note))
        if keep:
            parts = [x for x in parts if x["part"] in keep]
            label = "Rules"
    items = []
    for x in parts:
        cite = ELEMENT_RULES[x["part"]]
        if resolve:
            cite = resolve(cite, as_of(card["card_id"])) or cite
        items.append(f"{x['name']}: {cite}")
    return f"{label}: " + "; ".join(items) + "." if items else ""


def chat(model, prompt, max_tokens):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0,
                       "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(f"{API}/chat/completions", data=body, headers={"Content-Type": "application/json",
                                                                               "Authorization": "Bearer lm-studio"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]["content"].strip()


def notes(writer):
    return {r["card_id"]: r["note"] for r in map(json.loads, open(OUT / f"notes_{writer}.jsonl"))}


def judge(writer):
    cs, ns = cards(), notes(writer)
    path = OUT / f"judge_{writer}.jsonl"
    done = {json.loads(l)["card_id"] for l in open(path)} if path.exists() else set()
    with open(path, "a") as fh:
        for cid, note in ns.items():
            if cid in done:
                continue
            names = [x["name"] for x in cs[cid]["check_first"]]
            raw = chat("google/gemma-4-31b", JUDGE.format(note=note, parts="; ".join(names)), 200)
            m = re.search(r"\{.*\}", raw, re.S)
            try:
                got = json.loads(m.group(0))["parts"] if m else None
            except (json.JSONDecodeError, KeyError):
                got = None
            fh.write(json.dumps({"card_id": cid, "parts": got, "raw": None if got is not None else raw}) + "\n"); fh.flush()


def score():
    sys.path.insert(0, str(SPD))
    os.environ.setdefault("STATE_POLICY_CORPUS", str(SPD / "corpus"))
    from mcp_server.policy_index import get_index, resolve_citation
    ix = get_index()
    cs = cards()
    resolved = {}
    for c in cs.values():
        for x in c["check_first"]:
            if x["part"] in ELEMENT_RULES:
                key = (ELEMENT_RULES[x["part"]], as_of(c["card_id"]))
                if key not in resolved:
                    resolved[key] = "error" not in resolve_citation(ix, *key)
    out = {"cards": len(cs), "citations_resolve": round(sum(resolved.values()) / len(resolved), 3)}
    for writer in ("e2b", "e4b"):
        if not (OUT / f"notes_{writer}.jsonl").exists():
            continue
        ns = notes(writer)
        chk = C.score(cs, list(ns), ns)
        jp = OUT / f"judge_{writer}.jsonl"
        ref = {r["card_id"]: r["parts"] for r in map(json.loads, open(jp))} if jp.exists() else {}
        name_to_part = {}
        tp = fp = fn = tp_all = fp_all = exact = judged = empty = 0
        for cid, note in ns.items():
            c = cs[cid]
            mapped = {x["part"] for x in c["check_first"] if x["part"] in ELEMENT_RULES}
            det = set(named_parts(c, note)) & mapped
            empty += not det
            got = ref.get(cid)
            if got is None:
                continue
            judged += 1
            name_to_part = {x["name"].lower(): x["part"] for x in c["check_first"]}
            truth = {name_to_part.get(str(g).lower().strip()) for g in got} & mapped
            listed = det or mapped  # the filtered line falls back to all mapped parts
            tp += len(listed & truth); fp += len(listed - truth); fn += len(truth - listed)
            tp_all += len(mapped & truth); fp_all += len(mapped - truth)
            exact += listed == truth
        out[writer] = {"notes": len(ns), "pass_all_checks": round(chk["pass"], 3), "keeps_odds_and_benefit": round(chk["keeps_odds"], 3),
                       "words": round(chk["words"], 1), "grade": round(chk["grade"], 1),
                       "detector_found_nothing": round(empty / len(ns), 3), "judged": judged,
                       "unparsed_judgments": sum(1 for v in ref.values() if v is None)}
        if judged:
            out[writer].update({"filtered_precision": round(tp / max(1, tp + fp), 3), "filtered_recall": round(tp / max(1, tp + fn), 3),
                                "filtered_exact_match": round(exact / judged, 3), "all_line_precision": round(tp_all / max(1, tp_all + fp_all), 3)})
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"judge": lambda: judge(sys.argv[2]), "score": score}[sys.argv[1]]()

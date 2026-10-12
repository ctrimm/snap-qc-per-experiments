"""Exp 89 — exp88 follow-ups: a corrected judge, and citations moved to the end of the note.

Pre-registered (this docstring, committed before the scored runs):
  Part A, corrected judge. exp88's judge (Gemma 4 31B) counted the card's own instructions ("ask for the
  lease") as rule claims, and it saw excerpts cut at 900 characters. Judge v2: the full text of each
  cited section (up to 6,000 characters each), and an explicit exclusion of instructions, documents to
  request, household facts and card numbers. It re-judges exp88's plain and grounded notes unchanged.
  Part B, citations at the end. New arm grounded_end: the same excerpts as exp88's grounded arm, but
  the note keeps the plain style and ends with one line "Rules: <citation>; <citation>". Writer E4B
  (stock), temperature 0, 90 words for the prose. Judged with judge v2.
  Readouts per arm: citation coverage and unsupplied citations (as exp88); exp62's checks on the prose
  (citations and the Rules line removed), especially the reading-grade check; judge v2 rule claims per
  note and the share unsupported or contradicted. Paired bootstrap (seed 89) for pass rates
  grounded_end - grounded and grounded_end - plain.
  Hypotheses: H1 under judge v2, under 5% of grounded rule claims are unsupported or contradicted.
  H2 grounded_end recovers readability: its exp62 pass rate is within 3 points of plain (or above),
  with citation coverage still over 90%.

Usage: python experiments/exp89_rejudge_and_end_cites.py write | judge | score
"""
import json
import os
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_argv = sys.argv; sys.argv = sys.argv[:1]
import exp88_grounded_notes as E  # noqa: E402
sys.argv = _argv

OUT = E.OUT
END_EXTRA = """

Rules for the parts to check (official text, trimmed):
{rules}

Changes for this note: write the note as usual (at most 90 words, no citations inside the sentences). Then add one last line that starts with "Rules: " and lists the citation for each part you tell the caseworker to check, exactly as written above, separated by semicolons. State what a rule requires only if the excerpt above says it."""
JUDGE2 = """You check notes written for SNAP caseworkers against official rule text.

Rule text:
{rules}

Note:
{note}

List only statements in the note that say what a SNAP rule requires, allows, counts as income, excludes, or deducts.
Do NOT list: instructions to the caseworker (what to check, what to ask for, which documents to request), facts about this household or case, priority or expected-error figures, odds such as "6 of 10", or citations by themselves.
For each listed statement, say whether the rule text supports it. Answer with JSON only: {{"claims": [{{"text": "...", "verdict": "supported" | "unsupported" | "contradicted"}}]}}. If there are no such statements, answer {{"claims": []}}."""


def full_excerpts(c):
    """Like E.excerpts but the full cited text (up to 6,000 characters each) for the judge."""
    sys.path.insert(0, str(E.SPD))
    from mcp_server.policy_index import get_index, resolve_citation
    from datetime import date
    year = int(c["card_id"].split("-")[-2])
    as_of = max(date(year, 7, 1), date(2024, 1, 1))
    out = []
    for x in c["check_first"]:
        cite = E.ELEMENT_RULES.get(x["part"])
        if cite:
            r = resolve_citation(get_index(), cite, as_of)
            if "error" not in r:
                out.append((x["part"], cite, " ".join(r["text"].split())[:6000]))
    return out


def write():
    path = OUT / "notes_grounded_end.jsonl"
    done = {json.loads(l)["card_id"] for l in open(path)} if path.exists() else set()
    with open(path, "a") as fh:
        for c in E.cards():
            if c["card_id"] in done:
                continue
            ex = E.excerpts(c)
            prompt = E.PROMPT.format(card=E.card_text(c)).replace("\n\nNote:", END_EXTRA.format(rules=E.rules_block(ex)) + "\n\nNote:")
            fh.write(json.dumps({"card_id": c["card_id"], "note": E.chat("google/gemma-4-e4b", prompt, 260),
                                 "cites": [e[1] for e in ex]}) + "\n"); fh.flush()


def judge():
    cmap = {c["card_id"]: c for c in E.cards()}
    for arm in ("plain", "grounded", "grounded_end"):
        src, path = OUT / f"notes_{arm}.jsonl", OUT / f"judge2_{arm}.jsonl"
        done = {json.loads(l)["card_id"] for l in open(path)} if path.exists() else set()
        with open(path, "a") as fh:
            for l in open(src):
                n = json.loads(l)
                if n["card_id"] in done:
                    continue
                rules = E.rules_block(full_excerpts(cmap[n["card_id"]]))
                raw = E.chat("google/gemma-4-31b", JUDGE2.format(rules=rules, note=n["note"]), 800)
                m = re.search(r"\{.*\}", raw, re.S)
                try:
                    claims = json.loads(m.group(0))["claims"] if m else None
                except (json.JSONDecodeError, KeyError):
                    claims = None
                fh.write(json.dumps({"card_id": n["card_id"], "claims": claims, "raw": None if claims is not None else raw}) + "\n"); fh.flush()


def prose(note):
    note = re.sub(r"(?im)^\s*rules?:.*$", "", note)
    return re.sub(r"\(\s*" + E.CITE_RE.pattern + r"\s*\)", "", note, flags=re.I).strip()


def score():
    cmap = {c["card_id"]: c for c in E.cards()}
    res = {}
    for arm in ("plain", "grounded", "grounded_end"):
        notes = {json.loads(l)["card_id"]: json.loads(l) for l in open(OUT / f"notes_{arm}.jsonl")}
        E.K.MAX_WORDS = 70 if arm == "plain" else 90
        m = {}
        for k, n in notes.items():
            given = {E.norm(c) for c in n["cites"]}
            found = {E.norm(c) for c in E.CITE_RE.findall(n["note"])}
            cov = sum(1 for c in given if any(f.startswith(c) or c.startswith(f) for f in found)) / len(given) if given else None
            chk = E.K.check(cmap[k], prose(n["note"]))
            m[k] = {"cov": cov, "unsup": any(not any(f.startswith(g) or g.startswith(f) for g in given) for f in found),
                    "pass": chk["pass"], "faithful": chk["faithful"], "readable": chk["readable"], "words": len(prose(n["note"]).split())}
        jp = OUT / f"judge2_{arm}.jsonl"
        j = {json.loads(l)["card_id"]: json.loads(l)["claims"] for l in open(jp)} if jp.exists() else {}
        claims = [c for v in j.values() if v for c in v]
        cov = [v["cov"] for v in m.values() if v["cov"] is not None]
        res[arm] = m
        print(arm, json.dumps({
            "notes": len(m), "citation_coverage": round(sum(cov) / len(cov), 3) if cov else None,
            "unsupplied_citation": round(sum(v["unsup"] for v in m.values()) / len(m), 3),
            "faithful": round(sum(v["faithful"] for v in m.values()) / len(m), 3),
            "readable": round(sum(v["readable"] for v in m.values()) / len(m), 3),
            "pass_exp62": round(sum(v["pass"] for v in m.values()) / len(m), 3),
            "prose_words": round(sum(v["words"] for v in m.values()) / len(m), 1),
            "judged": len(j), "unparsed": sum(1 for v in j.values() if v is None),
            "claims_per_note": round(len(claims) / max(1, len(j)), 2), "claims": len(claims),
            "unsupported_or_contradicted": round(sum(c.get("verdict") != "supported" for c in claims) / len(claims), 3) if claims else None}))
    for a, b in (("grounded_end", "grounded"), ("grounded_end", "plain")):
        ids = sorted(set(res[a]) & set(res[b]))
        d = [int(res[a][i]["pass"]) - int(res[b][i]["pass"]) for i in ids]
        rng = random.Random(89)
        bs = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(2000))
        print(f"pass {a} - {b}: {100 * sum(d) / len(d):+.1f} [{100 * bs[50]:+.1f}, {100 * bs[1949]:+.1f}]")


if __name__ == "__main__":
    {"write": write, "judge": judge, "score": score}[sys.argv[1]]()

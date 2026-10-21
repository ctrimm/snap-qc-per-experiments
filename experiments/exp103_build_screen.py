"""Exp103 screening set from results already in hand (ids only, written to snap-qc-data/derived; never committed):
  hard     every question any 2026-dated 31B full run got wrong (exp98 arms 3 and 4, exp100 full, exp102 arm 1),
           plus all citizenship questions and all difficulty-3 questions
  controls 40 questions every one of those runs got right (seed 103): a regression check
Usage: python experiments/exp103_build_screen.py
"""
import csv
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exp94_96_analyze as A  # noqa: E402

RUNS = ["exp98_logs/31b_agent_2026", "exp98_logs/31b_combo_think_verify", "exp100_logs/full_notes_verify",
        "exp102_logs/full_plain_date_notes"]
OUT = A.D / "exp103_screen"


def main():
    rows = {r["question_id"]: r for r in csv.DictReader(open(A.CORNELL, encoding="utf-8-sig"))}
    runs = {r: A.load(r) for r in RUNS}
    if any(v is None for v in runs.values()):
        import glob
        from inspect_ai.log import read_eval_log  # a run still in progress: use its scored samples
        for r, v in runs.items():
            if v is None:
                l = read_eval_log(sorted(glob.glob(str(A.D / r / "*.eval")))[-1])
                runs[r] = {str(s.id): {"ok": float(list(s.scores.values())[0].value or 0)} for s in l.samples if s.scores}
    ids = set(rows)
    wrong = {i for r in runs.values() for i in ids if i in r and not r[i]["ok"]}
    cit = {i for i in ids if rows[i]["error_element"].startswith("Citizenship")}
    d3 = {i for i in ids if rows[i]["difficulty_rating"].startswith("3")}
    hard = wrong | cit | d3
    allright = sorted(i for i in ids - hard if all(i in r and r[i]["ok"] for r in runs.values()))
    controls = random.Random(103).sample(allright, 40)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "screen_ids.txt").write_text("\n".join(sorted(hard | set(controls), key=int)) + "\n")
    (OUT / "groups.json").write_text(json.dumps({"hard": sorted(hard, key=int), "controls": sorted(controls, key=int)}))
    print(json.dumps({"hard": len(hard), "wrong_in_some_run": len(wrong), "citizenship": len(cit), "difficulty3": len(d3),
                      "controls": len(controls), "total": len(hard) + len(controls),
                      "runs_n": {r: len(v) for r, v in runs.items()}}))


if __name__ == "__main__":
    main()

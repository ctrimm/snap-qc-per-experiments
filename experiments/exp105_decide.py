"""Exp105 between parts. `config`: apply the part-0 rule (P0-C >= P0-A - 2 points -> cite-only + curated, else
cite-only) and print the -T arguments for part 1. `ids`: write the ids E4B labels `noncitizens` (not committed)."""
import collections
import glob
import sys
import sys as _s
from pathlib import Path

from inspect_ai.log import read_eval_log

HERE = Path(__file__).resolve().parent
_s.path.insert(0, str(HERE))
import exp94_96_analyze as A  # noqa: E402

OUT = A.D / "exp105"


def p0():
    a, c = A.load("exp105_logs/p0_A"), A.load("exp105_logs/p0_C")
    return A.acc(a), A.acc(c)


def main(cmd):
    OUT.mkdir(parents=True, exist_ok=True)
    if cmd == "config":
        a, c = p0()
        args = "-T cite_only=true -T curated=true" if c >= a - 2 else "-T cite_only=true"
        (OUT / "config.txt").write_text(f"P0-A {a}% P0-C {c}% -> {args}\n")
        print(args)
    elif cmd == "ids":
        l = read_eval_log(sorted(glob.glob(str(A.D / "exp105_logs/e4b_topic/*.eval")))[-1])
        lab = {str(s.id): (list(s.scores.values())[0].answer or "") if s.scores else "" for s in l.samples}
        ids = [i for i, t in lab.items() if "noncitizen" in t]
        (OUT / "noncit_ids.txt").write_text("\n".join(ids) + "\n")
        (OUT / "labels.json").write_text(__import__("json").dumps(collections.Counter(lab.values()).most_common()))
        print(len(ids))


if __name__ == "__main__":
    main(sys.argv[1])

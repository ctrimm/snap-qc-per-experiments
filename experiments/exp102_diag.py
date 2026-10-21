"""Exp102 diagnostic (post-hoc, chosen after arm 1's per-element losses): on the 177 wage, child support, other
unearned income, shelter and SUA questions, separate the corpus effect from the prompt effect.
  old corpus, plain agent   = exp98 arm 3
  new corpus, plain agent   = exp102 diag (no date, notes or precedence)
  new corpus, + prompt      = exp102 arm 1 (date + notes + precedence)
Writes a table between DIAG markers in exp102_combined_expanded_corpus.md and the vault note.
"""
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exp94_96_analyze as A  # noqa: E402
from exp99_analyze import fmt  # noqa: E402
from exp102_analyze import VAULT  # noqa: E402

old, diag, arm1 = A.load("exp98_logs/31b_agent_2026"), A.load("exp102_logs/diag_plain_new_corpus"), A.load("exp102_logs/full_plain_date_notes")
ids = sorted(set(diag or {}) & set(old or {}) & set(arm1 or {}))
t = ["| Same questions (n = %d) | Accuracy |" % len(ids), "|---|---|"]
for k, r in (("old corpus, plain agent (exp98-3)", old), ("new corpus, plain agent (diagnostic)", diag),
             ("new corpus, date + notes + precedence (arm 1)", arm1)):
    t.append(f"| {k} | {A.acc(r, ids)}% |")
p = ["| Effect (95% CI) | Difference |", "|---|---|",
     f"| corpus: new − old, plain agent | {fmt(A.boot(diag, old, ids, 102))} |",
     f"| prompt: date + notes + precedence − plain, new corpus | {fmt(A.boot(arm1, diag, ids, 102))} |"]
block = f"Diagnostic scored {datetime.now():%Y-%m-%d %H:%M} by `exp102_diag.py` (post-hoc).\n\n" + "\n".join(t) + "\n\n" + "\n".join(p) + "\n"
for f in (HERE / "exp102_combined_expanded_corpus.md", VAULT):
    s = f.read_text()
    f.write_text(re.sub(r"<!-- DIAG:START -->.*?<!-- DIAG:END -->", "<!-- DIAG:START -->\n" + block + "<!-- DIAG:END -->", s, flags=re.S))
print(block)

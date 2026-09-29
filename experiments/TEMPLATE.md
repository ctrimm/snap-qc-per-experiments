# Experiment chronicle template

Copy this file to `expN_<slug>.md` for each new experiment. Keep every entry
honest: negative results are data.

## Experiment N — <title>
**Date:** YYYY-MM-DD · **Code:** `experiments/expN_<slug>.py`

### Hypothesis
What we believe, stated so it can be wrong. Must tie back to the north star:
which validation gate does this move, and why does moving it matter?

### Method
What we did, concretely enough to rerun: data, model, features, metric,
baselines. Link the script and any config.

### Results
Numbers, with baselines. Tables over prose.

### Verdict
Did the hypothesis hold? What did we learn that changes the plan?

### Next steps
Concrete follow-ups, each small enough to be one experiment. Mark which one
is the recommended next run.

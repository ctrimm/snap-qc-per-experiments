# Experiment 79 — an underpayment-focused ranker

**Date:** 2026-10-10 · **Code:** `experiments/exp79_underpayment_ranker.py` (pre-registered in its docstring) · **Results:** `experiments/exp79_results.json`

### Question

The triage ranker targets total error dollars, which are mostly overpayments. Can a ranker built to find households being shorted (underpayments) do that job better, and what does it cost on total error dollars?

### Method

All 53 jurisdictions, exp68 holdouts. "Total" = the exp68 ranker. "Under" = the same two-part design trained on underpayments only (STATUS 3 cases' dollars), default settings. Both scored on the holdout's top 20% for underpayment dollars and for total error dollars.

### Results

| Top 20% of the queue, held-out cases (53-jurisdiction median) | Total-dollar ranker | Underpayment ranker |
|---|---|---|
| Underpayment dollars found, × random | 1.55× | **3.36×** |
| Total error dollars found, × random | **3.25×** | 1.29× |

- The underpayment ranker finds more underpayment dollars in **all 53** jurisdictions (range 1.22× in the Virgin Islands to 4.22× in Oregon).
- The total-dollar ranker is sometimes worse than random at finding underpayments (Alaska 0.65×, Florida 0.75×).
- Underpayments are a median 28% of error dollars (14% in Massachusetts to 54% in New Hampshire).
- Examples: Pennsylvania 2.05× → 3.90× for underpayments (total 3.48× → 1.32×); Texas 2.00× → 3.93×.

### Verdict

Held, and a clear trade-off: the two rankers do different jobs. A state focused on payment accuracy and its error rate uses the total-dollar ranker; a state that also wants to find households being shorted should run the underpayment ranker for part of its review budget, since the total-dollar ranker finds underpayments at only about 1.5× random.

### Next steps

1. Offer both rankers in the package, with a split of the review budget (for example 80% total, 20% underpayment) as a state option.
2. Measure the combined queue's lift on both targets.

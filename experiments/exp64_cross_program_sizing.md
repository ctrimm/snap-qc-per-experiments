# Experiment 64 — other programs SNAP households likely qualify for (first sizing)

**Date:** 2026-10-10 · **Code:** `experiments/exp64_cross_program_sizing.py` · **Results:** `experiments/exp64_results.json`

### Question

Cory's idea (Oct 9): can the information a state already holds for SNAP show which households likely qualify for other programs? This is a sizing pass, not a product: how many SNAP households per POC state fit simple rules for six programs where SNAP participation, or the facts in a SNAP case, go most of the way to eligibility.

### Method

FY2024 QC public-use file, all sampled households, weighted by FYWGT to monthly caseloads (national total 21.6M households, in line with the published FY2024 caseload of about 22M). Proxies from facts in the SNAP case (2024 poverty guideline):

| Program | Proxy |
|---|---|
| Free school meals (direct certification) | any member aged 5–17 |
| WIC | any member aged 0–4 (pregnancy isn't in the file) |
| LIHEAP energy help | household pays utilities |
| Lifeline phone/internet discount | every SNAP household (SNAP qualifies) |
| Medicare Extra Help / Savings Programs | a member 65+ and gross income ≤ 150% of poverty |
| Medicaid (adults, expansion states) | a member 19–64 and gross income ≤ 138% of poverty; TX has not expanded |

### Results

Share of SNAP households (households per month):

| | SNAP households | School meals | WIC | LIHEAP | Lifeline | Medicare help | Medicaid adults |
|---|---|---|---|---|---|---|---|
| US | 21.6M | 26% (5.7M) | 13% (2.9M) | 72% (15.6M) | 100% | 22% (4.8M) | 66% (14.3M) |
| PA | 1.05M | 25% (264k) | 12% (127k) | 87% (910k) | 100% | 20% (211k) | 70% (733k) |
| NY | 1.63M | 21% (335k) | 10% (169k) | 88% (1.43M) | 100% | 30% (488k) | 62% (1.01M) |
| TX | 1.44M | 36% (524k) | 20% (288k) | 67% (967k) | 100% | 22% (316k) | n/a (no expansion) |
| SD | 37k | 30% (11k) | 14% (5k) | 66% (24k) | 100% | 18% (6k) | 82% (30k) |
| UT | 82k | 28% (23k) | 17% (14k) | 57% (46k) | 100% | 14% (11k) | 86% (70k) |
| ID | 65k | 30% (20k) | 16% (10k) | 77% (50k) | 100% | 19% (13k) | 80% (52k) |

School-age children in SNAP households: 10.4M nationally (PA 469k, NY 626k, TX 1.0M).

### Verdict

Informative. The overlap is large: every SNAP household qualifies for Lifeline, about a quarter have school-age children, and around a fifth have a low-income member 65+ who likely qualifies for Medicare cost help. These are counts of **likely eligibility, not unmet need**. The QC file doesn't show who is already enrolled, and asset tests, immigration rules, LIHEAP funding caps and state program choices (for example, which states run Summer EBT) aren't modelled.

### Next steps

1. The gap that matters is eligible-but-not-enrolled. That needs a state's own data: match SNAP cases against WIC, Medicaid, Lifeline and LIHEAP enrollment lists.
2. Start where SNAP data is already allowed to flow and the rules are simplest: Medicare Extra Help/Savings Programs for 65+ households, and WIC for households with children under 5.
3. Check each state's consent and data-sharing terms before any matching.

# Alaska rows in the QC public-use extract — investigation note (2026-10-03)

## Verdict: NEITHER extract problem NOR source problem — the claim was a code-formatting artifact.

The `STATE` field in all five FY CSVs stores the FIPS state code as a bare **integer**, not a zero-padded string. Filtering for the string `"02"` matches nothing; Alaska rows are present under `"2"`.

## Evidence

**Step 1 — verify the claim in `~/workspace/snap-qc-data/raw/` (READ-ONLY, untouched).**
Counts of `STATE == 2` vs `STATE == "02"` per FY:

| FY | file | rows | STATE=="02" | STATE==2 (Alaska) |
|----|------|------|-------------|-------------------|
| 2020 | qc_pub_fy2020.csv | 27,112 | 0 | 260 |
| 2021 | qc_pub_fy2021.csv | 9,832 | 0 | 127 |
| 2022 | qc_pub_fy2022.csv | 41,391 | 0 | 227 |
| 2023 | qc_pub_fy2023.csv | 43,776 | 0 | 207 |
| 2024 | qc_pub_fy2024.csv | 44,891 | 0 | 546 |

Alaska is present in all five years. The 55 distinct `STATE` values are FIPS 1–56 (with non-existent codes 3, 7, 14, 43, 52 absent) plus 66 (Guam) and 78 (US Virgin Islands) — no padding anywhere in the column. The FY2024 tech doc's weighting tables (`techdocs/fy2024.txt`, Table II.2) independently confirm Alaska cases are in the FY2024 file, and the codebook defines `STATE` as "FIPS code for State or territory" (Alaska = 02).

**Step 2 — inspect the extract pipeline.**
`~/workspace/snap-qc-data/README.md` documents a direct download from https://snapqcdata.net/datafiles on 2026-09-28 (only quirk: site 403s plain curl, needs a browser User-Agent header). No download, filtering, or transformation scripts exist anywhere in `~/workspace/snap-qc-data/`. There is no state filter list that could have dropped Alaska; the extract is the upstream files as published.

**Step 3 — web search on FNS excluding Alaska from QC.** Not needed: local evidence is conclusive (Alaska is present under code `2` in every FY). A search would answer a different question than the one that actually occurred.

## Takeaway

`STATE` is integer-coded; use `STATE == 2` (or zero-pad to two chars at read time, e.g. `zfill(2)`) when matching FIPS codes. Anyone filtering with `"02"` will silently drop Alaska in every FY. Suggest adopting a canonical two-char `state_fips` derived column in the synthetic-data pilot's loader to prevent recurrence.

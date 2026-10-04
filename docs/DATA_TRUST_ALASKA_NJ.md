# Data-trust note: Alaska row counts and the published-vs-microdata gap (2026-10-04)

## What happened

On 2026-10-03 I reported that Alaska had zero rows in all five fiscal years of QC microdata (FY2020–2024). That was wrong. Direct `STATENAME` counts verified the same day:

| FY | Alaska rows |
|----|-------------|
| 2020 | 260 |
| 2021 | 127 |
| 2022 | 227 |
| 2023 | 207 |
| 2024 | 546 |

## Root cause

The `STATE` field is integer-coded FIPS. Filtering for the string `'02'` matched nothing — Alaska's rows were present all along, invisible to a string filter. The error was in the query, not the data. Lesson: validate code values against the codebook before asserting absence; a zero count is a claim about the filter as much as the file.

## The real story: published vs microdata

The correction surfaced a larger, genuine discrepancy. Alaska's published error rate vs the microdata-implied rate (exp33):

| FY | Published | Microdata |
|----|-----------|-----------|
| 2023 | 60.37% | 4.66% |
| 2024 | 24.66% | 5.63% |

New Jersey FY2025 collapsed to 6.86% (−7.47pp) in the same window.

These gaps are administration-shaped, not random noise: they reflect how states administer the program (waivers, caseload composition, QC sampling) rather than measurement error in either source. Treat published state error rates and microdata-derived rates as two different lenses — never interchangeable, and never averaged without saying which lens you're using.

## Implications for this repo

- Any cross-state comparison that mixes published rates with microdata rates inherits this gap. The six-state POC panel uses microdata throughout; keep it that way.
- State-level findings (especially AK, NJ) should carry the basis explicitly: "microdata FY2020–24" vs "published FY2025".
- The FY2025 microdata watch (`fy2025-qc-microdata-watch`) should check whether the AK/NJ compositions moved when the new file lands.

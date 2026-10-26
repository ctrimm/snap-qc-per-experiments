# Notes for agents working in this repo

## The one rule that matters most: no leaky features

- **Ranker inputs default to the leak-free feature set** (`SNAPQC_FEATURES=leakfree`, the default).
- **The QC file's "reported" fields are reviewer values.** `RAWGROSS`, `RAWNET`, `RAWERND`, `SHELDED`, `CERTHHSZ` and the like are what the QC reviewer recorded, so for error cases they hold the corrected values.
- **Don't pair them with the issued benefit.** Pairing them with `RAWBEN` (what the agency issued), or anything derived from it, leaks the error label. That inflated every ranker result from exp58 to exp105 (found in exp106; leak-free top-20% lift 2.70×, not 3.97×).
- **`SNAPQC_FEATURES=legacy`** exists only to reproduce or audit those old results.
- **Details:** the README section "Feature set: leak-free by default", and `experiments/exp106_giannella_comparison.md` / `exp107_leakfree_rebuild.md`.
- **Before adding any feature, ask:** "would a state agency have this value, as is, before a QC review?" The fields `FS*`, `RAW*` (except `RAWBEN`), `AMTERR`, `STATUS`, `ELEMENT*`, `NATURE*` and `E_FINDG*` are review outputs or reviewer-recorded.

## Working conventions

- **One experiment = `experiments/expNN_*.md` + script.** Pre-register before running, amend before running anything new, and fill results between `<!-- AUTO-RESULTS:START/END -->`. Add an index row in `README.md`.
- **The Cornell CalFresh quiz is evaluation-only.** Never train on it or commit its text, answer key or per-question outputs.
- **Whitepapers** live in `whitepaper/` and are built with `whitepaper/build_pdf.py`. `whitepaper/state_numbers.py check` must pass after any change to state figures.

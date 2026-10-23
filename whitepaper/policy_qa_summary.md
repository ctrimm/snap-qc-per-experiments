# Grounding an Open Model in SNAP Policy: What Tools, Retrieval and Routing Add on a CalFresh Benchmark

**October 23, 2026 · Research summary · Cory Trimm**

## Executive summary

Caseworkers and QC reviewers answer policy questions all day: does this income count, which deduction applies, is this noncitizen eligible on this date. A language model that answers them correctly, and says which rule it relied on, would save time and catch mistakes. This summary covers 22 experiments (exp84–105, October 10–23, 2026). They ask how far an open model running on a single desktop computer can get on CalFresh (California SNAP) policy questions when it can look rules up, rather than answering from memory.

The benchmark is Cornell's 500-question CalFresh quiz. Nava PBC has published results on it for frontier and open models. We reached five findings:

1. **Looking rules up helps the larger open model, but not the small one.**
   - **31B model:** Gemma 4 31B, with search and lookup tools over a dated policy corpus, went from 84.0% to 88.8% (+4.8 points, 95% interval +2.0 to +7.6). Answering as of June 2026, it reached **89.6%**, our best single setup. That's about 4 points above Nava's published 85.8% for the same model without tools, or about 28% fewer wrong answers.
   - **4B model:** Gemma 4 E4B, about 4 billion parameters, did not gain on the quiz from the same tools. It searched but rarely opened the documents it found.
2. **The score stopped rising after the first jump.** Seven further changes over ten days each moved the score by less than the run-to-run noise (about ±2.5 points), or lowered it: supersession notes, an answer check, extended thinking, a larger corpus of state letters, letter weighting, curated rule pointers, and a routing layer.
3. **Sending each question to the right setup works, but adds little.** A small model labels each question's topic, and immigration questions go to a setup that is told the date and that federal law has changed. In a fresh run committed in advance, this beat the plain agent by +1.6 points (+0.6 to +2.8). Citizenship questions went from 70.6% to 91.2%. The run's overall score was 89.8%, essentially the earlier best.
4. **How the policy library is organized matters as much as what's in it.** Adding 458 older California letters pushed the right document out of the top five search results for about 1 in 8 hard questions. Keeping those letters out of search but one citation link away, in the Open Knowledge Format, restored retrieval. Off-the-shelf embedding search did worse than plain keyword search on this legal text.
5. **What's left is mostly reasoning, not missing information.** Of the roughly 45 questions still wrong after routing, 27 were missed by every setup we tried. The model usually has the right rule and applies it wrong, for example in self-employment arithmetic, medical deductions or net income. A few answer keys are disputable.

**Bottom line:** a free, open model on one workstation reaches about 90% on this benchmark with policy lookup, against about 86% without. Untuned GPT-6 scores 92.2% without tools, and a tuned GPT-6 with web search scores about 98%. Closing that gap locally looks unlikely with prompt and library changes alone. The likelier route is a stronger model, or a frontier model consulted only on the questions where local setups disagree.

## What we tried, in plain terms

Think of the model as a new caseworker taking a policy test. We tried several ways of helping it:

| What we tried | The caseworker equivalent | Did it help? |
|---|---|---|
| Let it look rules up (search, open a regulation section, use a benefit calculator) | An open-book test with the policy manual | **Yes, for the larger model** (+4.8). The small model flipped pages but didn't read them |
| Tell it what date the question is about | "Answer as of June 2026" | A little, within noise (+0.8) |
| Warn it when a federal law has overtaken a regulation | A sticky note: "this section changed in 2025" | Not by itself. Together with the date, it fixed most immigration questions |
| Ask it to check its own answer | "Read your answer once more before you hand it in" | Only when it had also been given passages and extended thinking time; otherwise no effect |
| Let it think longer before answering | More time on the test | Slightly, within noise (+1.8 without tools) |
| Give it hundreds more California policy letters | A much thicker binder, including old memos | **No, it hurt** (−3.4). Old memos crowded out current rules in search |
| Keep the old letters reachable only through citations | Old memos filed away but cross-referenced from current rules | Restored search quality; neutral on the test |
| Point it straight at the standing guidance for 8 common topics | Tabs in the binder for the most-used sections | Helped on our own questions (+3.3), not on Cornell's (−1.4, within noise) |
| Teach the small model the large model's habits | Shadowing a senior colleague | It learned the habits but got stuck searching and stopped answering |
| Route each question to the best setup | A supervisor who sends immigration questions to the specialist | **Yes** (+1.6), almost all on citizenship |
| Ask the model how confident it is, to decide when to escalate | "Are you sure?" | **No.** The model was as confident when wrong as when right |

## The benchmark and the comparison

**The quiz.** Cornell University's Benefits Gap Lab published 500 multiple-choice CalFresh questions, each a short client scenario (household, income, expenses, status) with five answer choices ([cornellbgl/SNAP_scenarios](https://huggingface.co/datasets/cornellbgl/SNAP_scenarios)). The licence (CC BY-NC-ND 4.0) allows evaluation only. We never trained on it, and we never published its questions, answer key or per-question predictions. Everything here is aggregate.

**When the quiz is set.** Our audit found that the quiz uses the FFY2026 standard utility allowance ($663). Six of its noncitizen answer keys follow the post-H.R. 1 rules that California applied from April 1, 2026. So the right date to answer "as of" is mid-2026, not before H.R. 1, and every setup from exp98 on answers as of June 1, 2026.

**Frontier results.** Nava PBC benchmarked frontier and open models on the same 500 questions ([Accuracy of AI models on SNAP questions](https://fieldnotes.navapbc.com/p/accuracy-ai-models-snap-questions); [What AI gets wrong about SNAP](https://fieldnotes.navapbc.com/p/what-ai-gets-wrong-about-snap-and)). We did not re-run their numbers. In their runs, with no tools and low reasoning effort, GPT-6 Astra scored 92.24% and Gemma 4 31B 85.8%, the best open model. Their roughly 98% result for GPT-6 used web search and a system prompt written after reviewing GPT-6's mistakes on these same questions. It shows what is possible, but it is partly tuned to the test.

| System | Cornell accuracy | Wrong of 500 | Source |
|---|---|---|---|
| Gemma 4 E4B (4B), no tools | 72.6–73.4% | about 135 | ours |
| Gemma 4 E4B, best tool setup | 77.0% | 115 | ours |
| Gemma 4 31B, no tools | 84.0% | 80 | ours |
| Gemma 4 31B, no tools (Nava's setup) | 85.8% | 71 | Nava; matched by our thinking run |
| **Gemma 4 31B with policy tools, as of June 2026** | **89.6%** | **52** | ours (exp98) |
| Gemma 4 31B with tools + topic router | 89.8% | 51 | ours (exp105, pre-registered) |
| GPT-6 Astra, no tools, untuned | 92.24% | about 39 | Nava |
| GPT-6, web search, tuned prompt | about 98% | about 10 | Nava |

Speed differs too. Our agent takes about 1.3 minutes a question, because it calls tools several times on a local machine. Nava's frontier runs take seconds.

## The policy library

The tools read from **state-policy-docs** ([github.com/ctrimm/state-policy-docs](https://github.com/ctrimm/state-policy-docs)), a corpus built for this work and served to the model through the Model Context Protocol (MCP):

- **Contents:** 4,461 documents in 20,843 searchable passages:
  - federal regulations (7 CFR 271–283);
  - the Food and Nutrition Act;
  - FNS guidance;
  - California's regulations (MPP 63) and policy interpretations;
  - 458 CDSS All County Letters and Information Notices;
  - other states' manuals.
- **Dates:** every document carries the dates it was in force, so the model can ask what the rule was on a given day.
- **Format:** the Open Knowledge Format (OKF v0.1), plain Markdown files with structured headers. Each document's first citation of another document is a link to it (2,672 links in 687 documents, none broken), which makes the corpus a navigable graph of rules.
- **Tools:**

  | Tool | What it does |
  |---|---|
  | `get_passages` | Keyword search, filtered to the question's date and state |
  | `lookup_rule` | 38 curated topics, each pointing at its governing federal and state rules and tables |
  | `get_section` | Opens a cited section, such as "7 CFR 273.9(d)(6)" or "ACL 21-101" |
  | `calculate_benefit` | The federal benefit formula |

## Results

### 1. Tools help the large model, not the small one

| Experiment | Setup | Accuracy | vs no tools (95% interval) |
|---|---|---|---|
| exp84 | E4B no tools → with tools | 71.6% → 68.6% | −3.0 [−6.8, +0.6] |
| exp85 | E4B, fuller rulebook, dated | 76.0% | +2.6 [−1.4, +6.8] |
| **exp86** | **31B no tools → agent with rule tools** | **84.0% → 88.8%** | **+4.8 [+2.0, +7.6]** (39 gained, 15 lost) |
| exp98 | 31B agent, as of June 1, 2026 | 89.6% | +0.8 vs exp86 [−1.4, +2.8] |

The 31B model opened the sections its search results cited (0.59 times a question); E4B almost never did, and answered from search snippets. On our own question sets, which are open-book by design, the gap is larger:
- **Hard set (224 questions), applied and date-sensitive:** 31B with tools 92.0%, E4B 82.1%.
- **E4B with a step-by-step tool recipe and date-filtered passages:** 88.8%, within 3 points of the 31B (exp95). On Cornell the same setup gained only +1.8.

### 2. The plateau

Every change after exp98 compared with the best plain agent (89.6%):

| Experiment | Change | Result |
|---|---|---|
| exp98 | Passages + extended thinking + an answer check | 89.2% (the check alone fixed 14 and broke 0 in that setup) |
| exp99 | Answer check on the plain agent | Fixed 1, broke 2 (−0.3); stopped early |
| exp100 | Supersession notes ("a statute changed this regulation") | 89.0%; the model read April 2026 as the future |
| exp101 | Date + notes + "follow the newer rule" | Citizenship 85.3% (vs 70.6%), 5 of 6 refugee/asylee questions |
| exp102 | The same on the corpus with 458 CDSS letters | 86.2% (−3.4 [−6.0, −0.8]); citizenship 91.2%, but income and deduction questions lost |
| exp103 | Letter weighting, screened on 193 hard questions | No arm beat the old corpus |
| exp105 | Cite-only letters + curated guidance | 88.2% (−1.4 [−3.6, +0.8]) |

Rerunning the same setup changes about 4% of answers, so differences under about 2.5 points on 500 questions are noise.

### 3. Routing

Different setups get different questions right. A perfect chooser between the plain agent and the date + notes setup would score 92.6%; adding the combined setup raises that to 94.6%. exp104 measured which cheap signals could do the choosing:

| Signal | Does it flag the plain agent's mistakes? (AUROC; 0.5 = no better than chance) |
|---|---|
| The model's stated confidence (31B or E4B) | 0.53 (no) |
| Agreement across 5 answers at temperature 0.7 | 0.50–0.52 (no) |
| No-tool answer differs from the agent's | 0.64–0.67 (some) |
| Two setups give different answers | 0.69–0.71 (best) |
| A model labels the topic "noncitizens" | 0.56–0.57 (narrow, but precise) |

A learned router combining these signals cross-validated at 90.0%, below the simple topic rule, so we used the topic rule. In the pre-registered test (exp105):

| Cornell, 500 questions | Accuracy | Citizenship (34) |
|---|---|---|
| Plain agent | 88.2% | 70.6% |
| **Topic router** (35 questions sent to date + notes; 9 answers changed) | **89.8%** | **91.2%** |
| Router − plain, paired | **+1.6 [+0.6, +2.8]** | |

The router cost 46 extra minutes on 500 questions. It passed its primary test, but missed the pre-registered 91% target. The plain agent in that run was 1.4 points lower than the earlier best.

### 4. Retrieval: organization beats size

Share of questions whose gold document is in the top five search results (exp104):

| Library and search | Our hard set (224) | California QA pairs (420) |
|---|---|---|
| Before the letters were added | 82.6% | 96.4% |
| Letters in search (keyword) | 70.1% | 86.4% |
| + strong down-weighting of old letters | 78.1% | 87.6% |
| Embeddings only (nomic-embed-text-v1.5) | 55.4% | 64.8% |
| Keyword + embeddings (hybrid) | 67.9% | 76.4% |
| **Letters cite-only (reachable through links)** | **81.2%** | **96.2%** |

Legal text rewards exact terms ("7 CFR 273.9", "categorical eligibility"). A small general-purpose embedding model lost to keyword search in every case. Federal and other-state retrieval was unaffected by the California letters (98.6% and 97.7%).

### 5. What remains

After the topic router, about 45 questions are wrong:
- 18 were answered correctly by some setup we ran, so better routing could recover them;
- 27 were missed by every setup;
- 2 have disputable answer keys.

The largest groups are self-employment (8), medical deductions (5), and 3 each for shelter, utility allowance, net income, citizenship, SSI and wages. The earlier audit (exp98) found 5 disputable keys across the quiz, which puts the practical ceiling near 99%.

## What did not work, and why it's worth knowing

- **Training the small model to imitate the large one (exp92, exp96).** E4B learned to open sections (0 → 1.17 a question) but lost 10.8 points. The cause was a training-data defect: the tool that records the conversations drops the final "submit answer" step, so the trained model never answered. Forcing an answer restored its base score. It did not add skill.
- **Self-reported confidence.** Both models were as confident on wrong answers as on right ones, so "ask the model if it's sure" can't decide when to escalate.
- **A bigger library.** More documents made search worse until the library was reorganized.
- **Prompt tweaks.** Each prompt change fixed one group of questions and broke another (exp102 fixed citizenship and broke income).

## Limitations

- **One benchmark, one state.** Cornell's quiz is California-specific, multiple-choice, and fixed at a 2026 rule set. Our own question sets are open-book by design (their answers come from the same tables the tools read), so they overstate real-world accuracy.
- **Tuning to the test.** From exp98 on, each change was chosen after looking at Cornell's misses. Only exp105 was a fresh, pre-registered test, and it confirmed the router but not the corpus change.
- **Noise.** About ±2.5 points on 500 questions. Most single-experiment differences fall inside it.
- **Speed.** About 1.3 minutes a question on a Mac Studio, which is too slow for live use without more hardware or a smaller loop.
- **Frontier numbers are Nava's,** run with their setup. We did not re-run them.

## Recommendations

1. **Use the 31B model with the policy tools, plus the topic router,** as the local baseline (about 90%). For any caseworker-facing use, show the rule it cited: in our flag-card work, model notes grounded this way named the governing rule for 97% of checks, with no invented citations (exp88, exp97).
2. **Stop tuning against Cornell.** Further prompt and library changes are unlikely to move the score beyond noise, and each one risks fitting the test.
3. **If accuracy above 92% matters, add a second opinion only where setups disagree.** Disagreement is the one signal that flags mistakes. A frontier model, or a stronger open model, consulted on the 10–15% of disputed questions would cost cents per 500 questions. Its errors would differ from Gemma's, which is what routing needs.
4. **Keep the library organized as a graph.** Cite-only letters and citation links fixed retrieval without deleting anything. Use the same approach as more states' letters are added.
5. **Build a held-out test of our own** (new scenarios, other states, written answers) before claiming any further gain.

## Technical reproduction

All code is in [ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments) (`experiments/`). The corpus and MCP server are in [ctrimm/state-policy-docs](https://github.com/ctrimm/state-policy-docs). Each experiment's write-up (`experiments/expNN_*.md`) holds its pre-registration, amendments and results.

### Environment

- **Hardware:** Mac Studio M3 Ultra, 256 GB.
- **Models:** LM Studio serving `google/gemma-4-31b` (19.9 GB GGUF) and `google/gemma-4-e4b` through its OpenAI-compatible API at `http://localhost:1234/v1`.
- **Harness:** Inspect AI 0.3.278 on Python 3.12, using the state-policy-docs virtualenv.
- **The quiz:** download `snap_scenarios.csv` from [cornellbgl/SNAP_scenarios](https://huggingface.co/datasets/cornellbgl/SNAP_scenarios) into `~/datasets/snap_scenarios/`. It's evaluation-only; don't commit it or any per-question output.

Load the 31B with enough context for each parallel slot. LM Studio splits the loaded context across slots, so 262,144 tokens with 4 slots gives about 65k each. Then set up the shell:

```bash
lms load google/gemma-4-31b --context-length 262144 --parallel 4 -y
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
SPD=~/Documents/GitHub/state-policy-docs     # corpus + MCP server
I=$SPD/.venv/bin/inspect
```

### Finding 1: policy tools lift the 31B (exp86, exp98-3)

```bash
cd experiments
# no tools
$I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-31b -M responses_api=false \
  -T mode=notools --max-connections 4 --log-dir LOGS/31b_notools
# agent with the four state-policy-docs tools, answering as of June 1, 2026 (exp98-3: 89.6%)
$I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-31b -M responses_api=false \
  -T mode=agent -T as_of=2026-06-01 --max-connections 4 --retry-on-error 2 --log-dir LOGS/31b_agent_2026
```

- **`-T as_of`:** in agent mode the task starts the MCP server (`mcp_server/server.py`) with `STATE_POLICY_DEFAULT_AS_OF` set, so tools return the rules in force on that date.
- **Our run** used state-policy-docs at the corpus before the letters import (commit `34f2813`). Check that commit out in a separate worktree to match it exactly.
- **Run time:** about 10.5 hours.
- **Expected result:** 88.8–89.6% ± 2.5.

### Finding 3: the topic router (exp105)

`experiments/queue_exp105.sh` runs the whole pre-registered experiment. Its steps:

```bash
# 1. topic labels from E4B (2 minutes); labels are aggregate-safe but the id list stays out of git
$I eval exp104_signals_task.py@signals --model openai/google/gemma-4-e4b -M responses_api=false -T mode=topic \
  --max-connections 4 --log-dir LOGS/e4b_topic
python exp105_decide.py ids            # writes snap-qc-data/derived/exp105/noncit_ids.txt
# 2. plain agent on all 500 (cite-only letters + curated guidance, as run)
$I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-31b -M responses_api=false \
  -T mode=agent -T as_of=2026-06-01 -T cite_only=true -T curated=true \
  --max-connections 4 --retry-on-error 2 --log-dir LOGS/plain
# 3. date + notes + precedence on the noncitizens-labeled questions only
$I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-31b -M responses_api=false \
  -T mode=agent -T as_of=2026-06-01 -T cite_only=true -T curated=true \
  -T date_in_prompt=true -T supersession=true -T precedence=true -T subset=ids:PATH/noncit_ids.txt \
  --max-connections 4 --retry-on-error 2 --log-dir LOGS/datenotes_noncit
# 4. score: router = step 3's answer on routed questions, step 2's elsewhere; paired bootstrap
python exp105_analyze.py
```

- **state-policy-docs commit:** `81f49839`.
- **Run time:** about 12 hours.
- **Bootstrap:** `exp94_96_analyze.boot` resamples question-level differences 2,000 times (seed 105) and reports the 2.5th and 97.5th percentiles.

### Finding 4: retrieval (exp104)

No model is needed, apart from the embedding model for the dense and hybrid rows:

```bash
cd experiments; P=$SPD/.venv/bin/python; C=$SPD/corpus
STATE_POLICY_CORPUS=$C                                   $P exp104_retrieval.py current
STATE_POLICY_CORPUS=$C STATE_POLICY_CITED_LETTERS=cite_only $P exp104_retrieval.py cite_only
STATE_POLICY_CORPUS=$C STATE_POLICY_LETTER_DECAY=1 STATE_POLICY_LETTER_WEIGHTS="3:1,10:0.4,*:0.15" \
                                                         $P exp104_retrieval.py decay_strong
# dense / hybrid: load the embedding model with 8k context first (2k context fails on long passages)
lms load text-embedding-nomic-embed-text-v1.5 --context-length 8192 -y
STATE_POLICY_CORPUS=$C STATE_POLICY_RETRIEVAL=hybrid     $P exp104_retrieval.py hybrid
```

- **Question sets:** the 224-question hard set (`experiments/exp94_hard.jsonl`, with gold document paths) and the 2,658 verified QA pairs in state-policy-docs.
- **Embedding cache:** the first dense run embeds all passages, about 10 minutes, and caches them in `.cache/dense/`.
- **"Before the letters" row:** run the same command against a worktree at `34f2813`.

### The corpus

```bash
cd $SPD
.venv/bin/python -m unittest discover -s tests      # 65 tests
.venv/bin/python pipeline/link_citations.py --dry  # OKF citation links (idempotent)
.venv/bin/python pipeline/check_links.py           # every internal link resolves
```

Server options (environment variables, all off by default):
- `STATE_POLICY_CITED_LETTERS=cite_only`
- `STATE_POLICY_CURATED_GUIDANCE=1`
- `STATE_POLICY_SUPERSESSION=1`
- `STATE_POLICY_LETTER_DECAY=1`
- `STATE_POLICY_RETRIEVAL=bm25|dense|hybrid`

## Experiment timeline

| When | Experiments | Milestone |
|---|---|---|
| Oct 10–11 | exp84–85 | Tools don't help E4B on Cornell; a fuller rulebook narrows the loss |
| Oct 11 | exp86–88 | Tools lift the 31B by +4.8; our own dated question set; rule-grounded flag-card notes |
| Oct 12 | exp89–92 | Harder questions; a tool recipe for E4B; distilling the 31B's tool use into E4B fails |
| Oct 15–16 | exp93–97 | 224-question hard set; the distillation failure traced to a training-data defect; Rules line at scale |
| Oct 17–18 | exp98 | Quiz audit and 2026 dating; best single setup 89.6% |
| Oct 19–21 | exp99–103 | Answer check, supersession notes, the date, 458 CDSS letters imported; none beats 89.6% |
| Oct 22 | exp104 | Routing signals, retrieval diagnosis, OKF citation links, cite-only letters |
| Oct 22–23 | exp105 | Pre-registered router: +1.6 over plain; 89.8% |

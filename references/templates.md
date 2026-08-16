# Artifact templates

Skeletons for each stage's file. Adapt headings to the field; keep the required
fields — later stages read them. Citation keys come from `library.json`
(`litsearch.py list`). Mark anything you did not verify with `[unverified]`.

---

## 01-idea.md

```markdown
# Idea: <working title>

## Raw idea
<the user's words, verbatim>

## Restatement
<one sentence>

## Context
- Problem: | Who is blocked: | Why now:
- Target venue / deadline: | Resources available (compute, data, code):

## Claim candidates
| # | Claim | Ambition | Falsified if | Defensible? |
|---|-------|----------|--------------|-------------|
| 1 |  | narrow |  |  |

**Primary claim:** <the one to defend>
**Falsification condition:** this claim is wrong if <observable outcome>

## Assumptions (attack surface)
1. <assumption> — plausible because … / untested

## Scope
In: … | Out: … | Explicitly not claiming: …

## Open questions for the user
```

---

## 02-related-work.md

```markdown
# Related work

## Queries run
| Query | Source(s) | Kept |
|-------|-----------|------|

## Landscape
### Cluster A — <name>
- **Approach:** <what these share mechanically>
- **Representative:** [key1] Title (venue, year); [key2] …
- **Core assumption:** …
- **Ceiling:** where this family stops, and the evidence for that

## Nearest works
| Key | Why close | Precise delta vs our idea | Read depth |
|-----|-----------|---------------------------|------------|
| [key] |  |  | full / method+limits / abstract |

## White space
- Nobody has: … (searched: "<queries>")

## Timeline
<what changed in the last 2-3 years and why>
```

---

## 03-benchmarks.md

```markdown
# Benchmarks & evaluation

| Benchmark | Measures | Size/splits | Metric(s) | SOTA (cite) | Protocol | Access |
|-----------|----------|-------------|-----------|-------------|----------|--------|

## Metric pathologies
- <metric>: hides <failure mode> — see [key]

## Blind spots
- No standard benchmark measures <X>; consequence: …

## Proposed evaluation set
- Primary: … because it directly tests <claim component>
- Secondary: …
- Baselines: strongest [key] | cheap-but-embarrassing … | nearest work [key]
- Cost per run: …
```

---

## 04-methodology.md

```markdown
# Methodology landscape

## Family A — <name>
**Mechanism.** Input → representation → key operation → output.
**Optimizes.** … **Therefore ignores.** …
**Cost.** train / inference **Failure regime.** …
**Source read:** [key] (sections …)

## Comparison
| Method | Assumption | Supervision | Cost | Fails when | Degrades to |
|--------|------------|-------------|------|------------|-------------|
| **Ours (proposed)** |  |  |  |  |  |

## Practical realities
- [key]: requires <trick> to work; sensitive to <hp>
```

---

## 05-challenges.md

```markdown
# Challenges, limitations, fallbacks

## Limitations
| # | Limitation | Evidence (cite + where) | Type | Severity | Attacked by | Outcome |
|---|-----------|-------------------------|------|----------|-------------|---------|
| L1 |  | [key] §6 | fundamental / incidental | blocking |  | still open |

## Fallbacks in the wild
| Method | When assumption breaks | What it falls back to | Acknowledged? |
|--------|------------------------|-----------------------|---------------|

## Live limitations (ranked by impact × tractability)
1. **L<n>** — impact: … tractability: … why now: …
```

---

## 06-alignment.md

```markdown
# Alignment: idea vs limitations

## Matrix
| Limitation | Addressed? | By what mechanism | Evidence that would prove it |
|------------|-----------|-------------------|------------------------------|
| L1 | direct / partial / no |  |  |

## Subsumption check
- Searched: "<queries>" → closest: [key]
- Does it subsume? no — because <specific difference> / yes — see below

## Diagnosis
<idea solves nothing live | incidental only | fundamental-under-assumption | subsumed>

## Sharpened claim
For **<setting>**, **<mechanism>** removes **<limitation L#>** that **<family>**
cannot, demonstrated by **<benchmark + metric>**.

## Decision
keep / sharpen / re-target / pivot — **user confirmed:** yes/no
Dropped from the original idea: …
```

---

## 07-refine.md

```markdown
# Refinement: challenge → solution → benchmark

## Contribution 1
- **Challenge (L#, [key]):**
- **Solution:** <component of the method>
- **Benchmark:** dataset / metric / baselines / expected effect size
- **Falsified if:** <result that kills it>

## Coverage check
| Contribution | Experiment | Baseline present | Falsifiable |
|--------------|-----------|------------------|-------------|

## Paper skeleton
- **Title candidates:** …
- **Abstract:** <written prose, 150-200 words>
- **1 Introduction:** problem matters → prior work stops here [cite] → we do X → we show Y
- **2 Related work:** clusters from 02, ending on the gap
- **3 Method:** mechanism, assumptions, complexity
- **4 Experiments:** setup, main table, ablations per contribution
- **5 Limitations:** the honest ones from our own 05
- **Figures:** Fig.1 mechanism | Fig.2 headline result | Tab.1 main comparison

## Experiment table shells
| Method | Bench A ↑ | Bench B ↑ | Cost |
|--------|-----------|-----------|------|
| baseline [key] | (reported: X, [key]) | | |
| **Ours** | TBD | TBD | TBD |

## Resource plan
| Experiment | Compute | Data | Have it? |
```

---

## 08-implement.md

```markdown
# Implementation

## Layout
impl/{data,methods,eval,configs}/ + run.py — entry point, config-driven

## Baseline reproduction (do this first)
| Baseline | Published (cite) | Reproduced | Gap | Explanation |
|----------|------------------|------------|-----|-------------|
> A gap that is not explained is a harness bug, not a footnote.

## Determinism
Seeds set for: … | Versions pinned: … | Same-seed reruns match: yes/no
Git commit at freeze: …

## Ablation switches (one per contribution)
| Contribution | Flag | Off = |
|--------------|------|-------|

## Smoke run
scale: … | metric produced: … | wall-clock: …

## Cost model
per run: … × runs … × seeds … = **total**; available: … ; verdict: fits / must cut
```

---

## 09-experiments.md

```markdown
# Experiments

## Registered protocols
| Name | Contribution | Hypothesis | Metric | Dataset | Seeds | Success threshold |
|------|--------------|-----------|--------|---------|-------|-------------------|
(registered with `exp.py register` BEFORE running)

## Main results
(paste `exp.py table --metric <m> --split dev`; test column filled once, at the end)

| Method | Bench A ↑ | Bench B ↑ | Cost | Source |
|--------|-----------|-----------|------|--------|
| baseline [key] | 0.00 ± 0.00 | | | reproduced / reported [key] |
| **Ours** | 0.00 ± 0.00 | | | this work, n=5 seeds |

## Statistical verdicts
(paste `exp.py compare <baseline> <ours> --metric <m>` per comparison)

## Ablations
| Variant | Δ vs full | Interpretation |
|---------|-----------|----------------|
> A contribution whose ablation doesn't hurt has no experimental support.

## Hypothesis verdicts
| Protocol | Success threshold | Result | Met? |
|----------|-------------------|--------|------|
> Failed hypotheses stay in this table.

## Failure analysis
Where the method still loses (regime, input type, %): …

## Protocol disclosures
seeds per arm: … | test evaluations used: __/__ | tuning budget: ours … vs baseline …
| deviations from the registered protocol and why: …
```

---

## LaTeX skeleton (`draft/paper.tex`)

Use when the user names a venue with a template; otherwise Markdown is fine.

```latex
\documentclass{article}          % swap for the venue style file
\usepackage{graphicx,booktabs,amsmath,hyperref}
\title{TITLE}
\author{AUTHORS}
\begin{document}
\maketitle
\begin{abstract}ABSTRACT\end{abstract}
\section{Introduction}           % 4 moves: matters / stops here / we do / we show
\section{Related Work}           % clusters from 02, ending on the gap
\section{Method}                 % mechanism, assumptions, complexity
\section{Experiments}            % setup, main table, ablation per contribution
\section{Limitations}
\section{Conclusion}
\bibliographystyle{plain}\bibliography{refs}
\end{document}
```

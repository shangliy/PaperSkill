---
name: paper
description: Research-paper pipeline that turns a raw idea into a defensible paper draft through staged research — idea intake → related work → benchmarks → methodology → challenges/limitations → idea-limitation alignment → challenge/solution/benchmark refinement → self-evolving critique rounds. Every stage writes a persisted artifact so the work is resumable and auditable. Use when the user has a research idea, wants a literature/benchmark/SOTA survey, wants to check novelty or positioning, wants to build or refine a paper outline or draft, or asks to "review/evolve/strengthen" a paper. Triggers: "paper", "research idea", "related work", "survey", "novelty check", "benchmarks", "写论文", "调研", "创新点".
---

# Paper Pipeline

Turns an initial idea into a paper draft through 8 gated stages. Each stage
produces a file in a workspace; nothing is done in-context-only, so the pipeline
survives session boundaries and can be re-entered at any stage.

`SKILL_DIR` below = the directory holding this SKILL.md (usually
`~/.claude/skills/paper`). Resolve it once with
`SKILL_DIR=$(dirname "$(readlink -f ~/.claude/skills/paper/SKILL.md)")` if a
command fails to find the scripts.

## Workspace layout

```
<workspace>/                     # default: ./papers/<slug>/
  state.json                     # stage status, meta, log  (managed by paper_state.py)
  library.json                   # retrieved literature      (managed by litsearch.py)
  refs.bib                       # exported bibtex
  experiments.json               # pre-registered protocols + change ledger (exp.py)
  results/runs.jsonl             # append-only run log (exp.py)
  01-idea.md  02-related-work.md  03-benchmarks.md  04-methodology.md
  05-challenges.md  06-alignment.md  07-refine.md  08-implement.md  09-experiments.md
  10-evolve/round-1.md ...
  draft/                         # paper draft (md and/or tex), created at stage 07
  impl/                          # method + baselines + eval harness, created at stage 08
```

## Dispatch

**Start / resume — always do this first.** If `state.json` exists anywhere under
`./papers/`, resume it; otherwise initialize:

```bash
python3 $SKILL_DIR/scripts/paper_state.py status --root "$PWD"        # resume: what's done, what's next
python3 $SKILL_DIR/scripts/paper_state.py init "<idea title>" --root "$PWD"
```

Then run the **next** incomplete stage. Do not skip forward: stage N's guide
assumes stages 1..N-1 exist on disk. If the user asks to jump ahead, say what
would be missing, then either backfill quickly or proceed with the gap recorded
in `state.json` via `note`.

Read `references/stage-guides.md` **before running any stage** — it holds the
per-stage procedure, output contract, and quality bar. Read
`references/templates.md` when creating an artifact file, and
`references/self-evolve.md` before stage 08.

| # | Stage | Artifact | One-line job |
|---|-------|----------|--------------|
| 01 | Idea intake | `01-idea.md` | Sharpen the raw idea into a falsifiable claim + scope + venue |
| 02 | Related work | `02-related-work.md` | Retrieve and cluster the literature landscape |
| 03 | Benchmarks | `03-benchmarks.md` | What datasets/metrics/baselines this field actually accepts |
| 04 | Methodology | `04-methodology.md` | Taxonomy of how existing methods work, with mechanisms |
| 05 | Challenges | `05-challenges.md` | Open problems, failure modes, the fallbacks SOTA relies on |
| 06 | Alignment | `06-alignment.md` | Score the idea against each limitation; keep, sharpen, or pivot |
| 07 | Refine | `07-refine.md` + `draft/` | Challenge → solution → benchmark triples → paper skeleton |
| 08 | Implement | `08-implement.md` + `impl/` | Harness + baselines + ablation flags; reproduce a baseline first |
| 09 | Experiments | `09-experiments.md` + `results/` | Pre-registered runs, ≥3 seeds, ablations, statistical verdicts |
| 10 | Self-evolve | `10-evolve/round-N.md` | Two loops — argument review + metric improvement — feeding back into 02–09 |

Mark stages complete as you go — the gate is not decorative, it is how a later
session knows what to trust:

```bash
python3 $SKILL_DIR/scripts/paper_state.py complete 02-related-work --summary "42 papers, 5 clusters; gap: no streaming eval" --root "$PWD"
```

## Literature retrieval

Use the script, not ad-hoc web search, for anything that becomes a citation —
it hits arXiv + OpenAlex + Semantic Scholar, dedupes, and persists to
`library.json` so later stages and the bibliography stay consistent.

```bash
python3 $SKILL_DIR/scripts/litsearch.py search "query terms" --tag 02-related-work --limit 25 --workspace <ws>
python3 $SKILL_DIR/scripts/litsearch.py search "query" --year-min 2023 --source arxiv,s2 --workspace <ws>
python3 $SKILL_DIR/scripts/litsearch.py list --tag 03-benchmarks --workspace <ws>
python3 $SKILL_DIR/scripts/litsearch.py bib --workspace <ws>          # → refs.bib
```

If a source 429s, the tool warns and continues on the others (arXiv blocks some
shared IPs outright; OpenAlex and Semantic Scholar both index arXiv preprints, so
coverage survives). Exit code 2 means *all* sources failed — pause ~30s, retry,
and fall back to WebSearch only if it persists.

Run 4–8 *differently phrased* queries per stage (problem phrasing, method
phrasing, application phrasing, the name of the closest known work). One query
is not a literature review. Then use WebFetch on the handful of papers that
actually matter — abstracts alone cannot support a claim about a method's
mechanism or a benchmark's protocol.

## Experiments

Stages 08–10 run and improve real experiments. Every run goes through the
tracker — a metric that is not in `results/runs.jsonl` cannot enter the paper.

```bash
EX="python3 $SKILL_DIR/scripts/exp.py --workspace <ws>"
$EX register main --hypothesis "..." --metric accuracy --dataset X --seeds 5 --success "+2.0 on dev"
$EX log main --metric accuracy=0.83 --seed 1 --split dev --config ctx=8192 --cost "1.4 GPU-h"
$EX table --metric accuracy --split dev      # mean ± sd, 95% CI, flags n<3
$EX compare baseline ours --metric accuracy  # noise band, Cohen's d, permutation p, verdict
$EX attempt --round 2 --change "..." --predicted "+1.5" --observed "+0.4" --verdict reject
$EX ledger ; $EX status                      # attempts kept/rejected; test-eval budget
```

Non-negotiables, because they are what make the numbers mean anything:
**register the protocol and its success threshold before running**; **≥3 seeds
per arm** (single-seed numbers are not results); **tune on dev, touch test once**;
and let `compare` decide — a gain inside the seed-noise band is not an
improvement, however much you want it to be.

## Rules

- **Cite or mark.** Every factual claim about prior work carries a citation key
  from `library.json`. Anything you inferred but did not verify gets an explicit
  `[unverified]` tag in the artifact. Never invent a paper, number, or venue.
- **Read the papers that carry weight.** A claim that a method fails in some
  regime requires reading that paper's limitations/experiments section.
- **The idea may lose.** Stage 06 is allowed to conclude the idea is subsumed by
  existing work. Report that plainly and offer the nearest surviving variant —
  do not quietly re-scope it into something defensible and call it the original.
- **Numbers come from sources or from runs.** Published results are copied with a
  citation; measured results come from `runs.jsonl` with seeds and a commit.
  Never estimate, interpolate, or "expect" a number into a table — planned
  experiments stay labeled as planned until they have run.
- **Failed experiments stay.** A hypothesis that missed its registered threshold
  is reported, not deleted or re-described as a success at a different metric.
- **Ask the user before pivoting the research direction** (stage 06 pivots, venue
  changes, dropping a contribution). Everything else is your call.
- Write artifacts in the language the user is using.

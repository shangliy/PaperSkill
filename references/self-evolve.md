# Stage 08 — Self-evolve

The loop that makes the pipeline more than a checklist: review the paper as a
hostile committee, convert findings into stage-level work, redo those stages,
re-review. The feedback edges are the point — a round that only edits prose is a
wasted round.

## Round procedure

```bash
python3 $SKILL_DIR/scripts/paper_state.py round --root "$PWD"   # opens 08-evolve/round-N.md
```

**1. Score, with evidence.** Fill the scorecard. Every score needs a sentence of
evidence pointing at the draft or an artifact — a bare number is noise.

| Axis | 1 | 3 | 5 |
|------|---|---|---|
| Novelty | subsumed by known work | delta exists but is incremental | new mechanism or new problem framing, checked against 02/06 |
| Significance | nobody is blocked by this | helps one niche | unblocks a limitation ranked live in 05 |
| Soundness | claim outruns the mechanism | mechanism plausible, gaps in argument | mechanism explains *why* it works, assumptions stated |
| Evaluation fit | benchmarks don't test the claim | tests the claim, weak baselines | tests the claim on accepted benchmarks vs the strongest baseline |
| Clarity | reader can't state the contribution | contribution stated, argument wanders | one claim, four intro moves, figure carries the mechanism |

**2. Run the reviewer panel.** Adopt each persona fully and separately — write
its findings before switching. Mixing them produces one bland reviewer.

- **R1, the area chair.** Reads only title, abstract, intro, Fig. 1, and the
  results table. Asks: what is the one contribution, and does the table support
  it? Writes the meta-review sentence that decides the paper.
- **R2, the domain expert.** Knows the 3 nearest works cold. Hunts for
  subsumption, misattributed novelty, missing citations, and mechanism claims the
  paper cannot support. Names specific papers.
- **R3, the empiricist.** Attacks the evaluation: missing baseline, favorable
  hyperparameters, cherry-picked splits, no variance/seeds, metric that hides the
  failure mode, ablation that doesn't isolate the claimed component.
- **R4, the skeptic.** Grants nothing. For each claim asks "what result would
  falsify this, and is that experiment in the plan?" Also asks what the method
  *costs* — compute, data, assumptions — and whether the gain survives it.

**3. Reproduce the strongest objection.** Pick the single finding most likely to
kill the paper and verify it against sources — search for the paper R2 claims
subsumes you, check the benchmark protocol R3 disputes. A review finding that
turns out to be false is worth removing before it drives a rewrite.

**4. Convert findings to actions.** Every surviving finding maps to a stage,
never to a vague resolution:

| Finding | Action |
|---------|--------|
| Missing/closer prior work | `PS reopen 02-related-work` → targeted searches → redo 06 subsumption check |
| Benchmark won't convince | `PS reopen 03-benchmarks` → add benchmark/baseline → update 07 triples |
| Mechanism doesn't explain result | `PS reopen 04-methodology` → sharpen mechanism or weaken claim |
| Limitation isn't real / not live | `PS reopen 05-challenges` → re-source it, or re-target |
| Claim outruns evidence | `PS reopen 06-alignment` → narrow scope to what the evidence covers |
| Contribution unfalsifiable | `PS reopen 07-refine` → add failure signal or drop the triple |

Do the actions *in this round*. A round ends with the artifacts changed, not with
a to-do list.

**5. Close the round.** Record in `round-N.md`: scores, findings (kept and
refuted), actions taken with the diff they produced, and the verdict — what
changed about the paper's argument. Then `PS complete 08-evolve --summary "..."`
or open the next round.

## Convergence

Stop when either holds:
- All axes ≥ 4, **and** a round produced no new blocking finding. Report the
  scorecard trajectory across rounds.
- Two consecutive rounds produce only cosmetic actions — the pipeline has given
  what it can; remaining risk is experimental, not analytical.

Hard stops that override convergence: the user says stop; the same finding
survives two rounds unfixed (escalate to the user — it is a research problem, not
a writing problem); or a round concludes the claim is subsumed (stop and report,
do not re-scope silently).

Diminishing returns are real — after round 3–4 without experiments, more review
mostly relitigates. Say so rather than looping for its own sake.

## Escalation ladder

Each round should push at a different layer, deepest last:

1. **Prose** — the claim is right, the writing hides it.
2. **Framing** — the contribution is real but pointed at the wrong limitation
   (reopen 06).
3. **Evidence** — the argument needs an experiment it doesn't have (reopen 03/07).
4. **Mechanism** — the method can't do what the claim says (reopen 04).
5. **Idea** — the delta doesn't survive the literature (reopen 02, then ask the
   user whether to pivot).

If two rounds in a row only reach layer 1, converge. If a round reaches layer 5,
stop and bring it to the user with evidence — that decision is theirs.

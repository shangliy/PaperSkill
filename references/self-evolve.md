# Stage 10 — Self-evolve

The loop that makes the pipeline more than a checklist. Each round runs **two**
loops and both feed back into earlier stages:

- **Loop A — argument.** A hostile committee reviews the paper; findings become
  stage work.
- **Loop B — metrics.** Diagnose where the number is lost, hypothesize a change,
  implement it, measure it honestly, keep it only if it survives the noise band.

A round that only edits prose is a wasted round. A round that only chases metrics
produces a stronger number attached to a weaker paper. Run both.

```bash
python3 $SKILL_DIR/scripts/paper_state.py round --root "$PWD"   # opens 10-evolve/round-N.md
```

`EX` = `python3 $SKILL_DIR/scripts/exp.py --workspace <ws>`
`PS` = `python3 $SKILL_DIR/scripts/paper_state.py`

---

## Loop A — argument review

**1. Score, with evidence.** Every score needs a sentence pointing at the draft
or an artifact — a bare number is noise.

| Axis | 1 | 3 | 5 |
|------|---|---|---|
| Novelty | subsumed by known work | delta exists but is incremental | new mechanism or new problem framing, checked against 02/06 |
| Significance | nobody is blocked by this | helps one niche | unblocks a limitation ranked live in 05 |
| Soundness | claim outruns the mechanism | mechanism plausible, gaps in argument | mechanism explains *why* it works, assumptions stated |
| Evaluation fit | benchmarks don't test the claim | tests the claim, weak baselines | accepted benchmarks, strongest baseline, ≥3 seeds, ablation per claim |
| Reproducibility | numbers unlinked to code/config | code exists, protocol partly documented | seeds/configs/commits logged, baseline reproduced, budget disclosed |
| Clarity | reader can't state the contribution | contribution stated, argument wanders | one claim, four intro moves, figure carries the mechanism |

**2. Reviewer panel.** Adopt each persona fully and separately — write its
findings before switching, or they blur into one bland reviewer.

- **R1, the area chair.** Reads only title, abstract, intro, Fig. 1, and the main
  table. What is the one contribution, and does the table support it?
- **R2, the domain expert.** Knows the 3 nearest works cold. Hunts subsumption,
  misattributed novelty, missing citations, mechanism claims the paper can't
  support. Names specific papers.
- **R3, the empiricist.** Now has real numbers to attack: missing baseline,
  single seed, tuned-on-test, gains inside variance, ablation that doesn't
  isolate the claimed component, metric that hides the failure mode, cost hidden
  behind an accuracy gain. Checks `EX table` and `EX runs` against the paper.
- **R4, the skeptic.** Grants nothing. For each claim: what result would falsify
  it, was that experiment run, and what did it show? What does the method cost,
  and does the gain survive the cost?

**3. Reproduce the strongest objection** before acting on it — search for the
paper R2 says subsumes you, re-run the comparison R3 disputes. A false finding
that drives a rewrite is expensive.

---

## Loop B — empirical improvement

The goal is a better metric that is *real*. The whole discipline is the accept
rule: **a change is kept only if it beats the seed-noise band on dev, with the
protocol fixed in advance.**

**1. Diagnose before changing anything.** Never tweak hyperparameters hoping.
Locate the loss:
- Error analysis: sample 30–50 failures, cluster them by cause, count the
  clusters. The largest cluster is the target.
- Ablation attribution: which contribution actually carries the gain (`EX compare`
  against each ablation)?
- Regime analysis: split results by input length, class, difficulty, domain. Gains
  and losses usually live in a subset, not uniformly.
- Oracle/ceiling probe: replace one component with a perfect oracle. If the metric
  barely moves, that component is not where the headroom is — stop working on it.

**2. Hypothesize with a prediction.** Write the change, the mechanism by which it
should help, the *predicted* effect size, and what result would falsify it. A
change with no predicted mechanism is a lottery ticket, and it will not survive
R3 in the next round.

**3. Implement and measure.**
```bash
EX register c1-rerank --hypothesis "reranking evicted keys recovers the 18% recall-miss cluster" \
   --metric accuracy --dataset LongBench --seeds 5 --success "+1.5 acc on dev, cost <+15%"
EX log c1-rerank --metric accuracy=0.847 --seed 1 --split dev --commit $(git -C impl rev-parse --short HEAD)
EX compare ours c1-rerank --metric accuracy --split dev
```

**4. Accept or reject by the rule, not by hope.**

| `EX compare` verdict | What it means | Action |
|---|---|---|
| ACCEPT | gain > noise band and p < alpha | keep the change; update the method description in the draft |
| INCONCLUSIVE | gain > noise but p too high | add seeds — do not report it as a win |
| REJECT (inside noise) | not distinguishable from seed variance | revert; record it |
| REJECT (negative) | it hurts | revert; the *reason* often explains the mechanism |

Record every attempt, kept or not:
```bash
EX attempt --round 2 --change "rerank evicted keys" --predicted "+1.5 acc" \
   --observed "+0.4 acc, inside noise 0.6" --verdict reject
```
The ledger is what lets the paper say "we tried X and it did not help, because…",
which is both honest and one of the more useful paragraphs a reader gets.

**5. Guardrails — the ways this loop goes wrong.**
- **Test-set erosion.** Tune on dev; `exp.py` counts test evals against a budget.
  If the budget is spent, the honest move is to report the number you have and
  say how many times test was touched.
- **Seed lottery.** Never pick the best seed. Report mean ± sd over the
  registered seed count; a gain that only exists at seed 3 does not exist.
- **Baseline neglect.** Tuning your method for ten rounds against an untuned
  baseline manufactures a gain. Give the baseline the same tuning budget and say
  what it was.
- **Moving the metric.** Switching the headline metric after seeing results is
  post-hoc storytelling. Add metrics freely; change the headline only with a
  stated reason, recorded in the round file.
- **Cost blindness.** Log cost with every run. A +1 point gain at 3× compute is a
  different claim, and reviewers will price it.
- **Overfitting the loop itself.** If 5+ attempts have produced only
  inside-noise gains, the headroom is not in tuning — go back to Loop A layer 4
  (mechanism) or accept the result and write the honest paper.

---

## Converting findings to stage work

Both loops end in `PS reopen`, never in a vague resolution:

| Finding | Action |
|---------|--------|
| Missing/closer prior work | `PS reopen 02-related-work` → targeted searches → redo 06 subsumption check |
| Benchmark won't convince | `PS reopen 03-benchmarks` → add benchmark/baseline → update 07 triples |
| Mechanism doesn't explain the result | `PS reopen 04-methodology` → sharpen mechanism or weaken claim |
| Limitation isn't real / not live | `PS reopen 05-challenges` → re-source it, or re-target |
| **Results contradict the claim** | `PS reopen 06-alignment` → narrow the claim to what the evidence covers, or re-target |
| Contribution unfalsifiable / unsupported by its ablation | `PS reopen 07-refine` → add failure signal, or drop the triple |
| Harness bug, non-determinism, baseline not reproduced | `PS reopen 08-implement` → fix before any further tuning; results after a harness fix supersede results before it |
| Gain inside noise, missing seeds, missing ablation | `PS reopen 09-experiments` → more seeds / the missing arm |

Do the actions *in this round*. A round ends with artifacts changed and, for
Loop B, with `EX ledger` longer than it was.

---

## Convergence

Stop when **both** loops are quiet:
- Loop A: all axes ≥ 4 and a round produced no new blocking finding.
- Loop B: no dev gain above the noise band across the last 3 attempts, or the
  compute budget is spent.

Then run the final test-set evaluation **once**, report it with mean ± sd, and
freeze. If the test number is materially worse than dev, that gap is a finding
for the limitations section — not a reason to re-tune.

Hard stops that override convergence: the user says stop; the same finding
survives two rounds unfixed (escalate — it is a research problem, not a writing
problem); a round concludes the claim is subsumed (stop and report); or the
results contradict the central claim (stop, bring it to the user — the honest
options are narrowing the claim or reporting a negative result, and that choice
is theirs).

## Escalation ladder

Each round should push at a different layer, deepest last:

1. **Prose** — the claim is right, the writing hides it.
2. **Tuning** — the mechanism is right, the configuration is not (Loop B).
3. **Framing** — the contribution is real but pointed at the wrong limitation
   (reopen 06).
4. **Evidence** — the argument needs an experiment it doesn't have (reopen 09).
5. **Mechanism** — the method can't do what the claim says (reopen 04/08).
6. **Idea** — the delta doesn't survive the literature or the results (reopen 02,
   then ask the user whether to pivot).

Two consecutive rounds that only reach layers 1–2: converge. A round that reaches
layer 6: stop and bring it to the user with the evidence — that decision is theirs.

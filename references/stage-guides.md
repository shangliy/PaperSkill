# Stage guides

One section per stage: what it is for, how to run it, what "done" means.
Read the section for the stage you are about to run. Artifact formats live in
`templates.md`; stage 08 has its own file, `self-evolve.md`.

Shortcuts used below:
- `PS` = `python3 $SKILL_DIR/scripts/paper_state.py`
- `LS` = `python3 $SKILL_DIR/scripts/litsearch.py --workspace <ws>`

---

## 01-idea — Idea intake

**Goal.** Convert whatever the user said into a claim that can be argued with.
A raw idea ("use RL for compiler scheduling") is not yet a paper; a claim is
("*learned* schedulers beat heuristics on unseen kernel shapes because they
transfer structure across shapes — and this can be shown on X").

**Procedure.**
1. Restate the idea in one sentence, then extract: problem, proposed mechanism,
   why-now, and who suffers today if this doesn't exist.
2. Ask the user for anything that changes the whole pipeline and cannot be
   guessed: target venue/deadline, whether compute/data for experiments exist,
   whether this must extend the user's own prior work. Ask these **together**,
   once. Do not ask what you can research (state of the field, baselines).
3. Write 3–5 *falsifiable* claim candidates at different ambition levels, and
   mark the one you'd defend. Ambition matters: the smallest claim is usually
   provable and unpublishable; the largest is usually neither.
4. List assumptions the idea silently depends on — these become the attack
   surface reviewers use in stage 08.
5. Record scope boundaries: what this paper is explicitly *not* about.
6. `PS set venue <V>`, `PS set domain <D>`, `PS set claim "<sentence>"`.

**Done when** the artifact has a single primary claim, its falsification
condition ("this claim is wrong if …"), assumptions, and scope boundaries.
Not done if the claim survives any experimental outcome.

---

## 02-related-work — Related work

**Goal.** A map of the field, not a pile of citations. The output must let you
answer: who else attacked this problem, in what families, and where each family
stopped.

**Procedure.**
1. Derive 5–8 query formulations from stage 01: problem phrasing, mechanism
   phrasing, application phrasing, the standard term of art, the adjacent field's
   term for the same thing, and the name of the closest known work.
2. Run them. Widen with `--year-min` off for foundational work, then narrow to
   the last 2–3 years for the frontier:
   ```
   LS search "<phrasing>" --tag 02-related-work --limit 25
   LS search "<phrasing>" --tag 02-related-work --year-min 2023
   ```
3. Triage by title+abstract. For the ~8–15 that matter, WebFetch the paper (arXiv
   abs/HTML page, or the PDF) and read method + limitations sections. Record what
   you read in each entry's use — a paper you only skimmed cannot support a claim
   about its mechanism.
4. **Follow the citation graph** both directions for the 3–5 closest works: their
   related-work section names the ancestors; searching their title finds the
   descendants. This is where the actually-closest paper usually hides.
5. Cluster into 4–7 families by *approach*, not by year or authorship. Name each
   family, give its representative works, its core assumption, and its ceiling.
6. Identify the 3 papers closest to the user's idea and state, in one line each,
   the precise delta between them and the idea. "They don't do X" is only valid
   if you checked that they don't.

**Done when** every cluster has a stated ceiling, the 3 nearest works have
explicit deltas, and you can name what nobody has tried. Not done while the
nearest-work delta is vague ("ours is more general").

---

## 03-benchmarks — Benchmarks

**Goal.** Know what evidence this community accepts, before designing anything.
A contribution evaluated on a benchmark nobody uses is unreviewable.

**Procedure.**
1. `LS search "<task> benchmark dataset evaluation" --tag 03-benchmarks` plus
   searches for the specific dataset names you saw in stage 02.
2. For each candidate benchmark record: what it measures, size/splits, the
   metric(s) and their known pathologies, the current SOTA number **with its
   citation**, and whether the protocol is standardized or per-paper.
3. Note access reality: license, download size, compute needed for one run,
   whether a public leaderboard exists. A benchmark the user cannot run is a
   different kind of fact than one they can.
4. Identify what the standard benchmarks *cannot* measure — the blind spot. This
   feeds stage 05 and is often the honest home of a new contribution.
5. Pick the evaluation set: 2–3 primary benchmarks + baselines that reviewers
   will demand (the obvious strong baseline, the cheap baseline that embarrasses
   complex methods, and the closest related work from stage 02).

**Done when** each proposed benchmark has SOTA + citation + a reason it is the
right test for *this* claim, and the blind spot is written down. Numbers without
citations are a defect, not a placeholder.

---

## 04-methodology — Methodology

**Goal.** Understand mechanisms well enough to predict where they break. This is
the stage that makes stage 05 non-generic.

**Procedure.**
1. For each family from stage 02, describe the actual mechanism: inputs,
   representation, the key operation, training/inference cost, what it optimizes
   and what it therefore ignores.
2. Build a comparison table across axes that matter for the claim (assumptions,
   supervision needed, cost, failure regime, what it degrades to).
3. Note engineering realities that papers bury: tricks required to make it work,
   hyperparameter sensitivity, unreported preprocessing.
4. Write the mechanism the user's idea would need, in the same vocabulary, and
   place it in the table. If it collapses into an existing row, say so now —
   that is a stage-06 finding arriving early, and it is cheap here, expensive
   after the experiments.

**Done when** each family has a mechanism paragraph tied to a paper you actually
read, and the idea sits in the same table with a distinguishable row.

---

## 05-challenges — Challenges, limitations, fallbacks

**Goal.** The field's real open problems, with evidence — plus the *fallbacks*:
what SOTA methods quietly do when their assumption fails (retry, back off to a
heuristic, restrict the input, hand-tune per dataset, cap the horizon). Fallbacks
are where papers are hiding their limitations, and where new work gets bought.

**Procedure.**
1. Mine sources in this order — the further down, the more honest: limitations
   sections, failure/ablation analyses, "future work", survey papers' open-problem
   sections, benchmark blind spots from stage 03, and reproducibility reports or
   public reviews (OpenReview) when available.
2. For each limitation record: statement, evidence (citation + where in the paper),
   severity (blocking / costly / cosmetic), how often it is acknowledged vs
   silently patched, and who has already attacked it and failed.
3. Separate **fundamental** limits (the assumption is the method) from
   **incidental** ones (scale, engineering, missing data). Papers that attack
   incidental limits get "not novel"; papers that attack fundamental ones get
   "too hard" — knowing which you have determines how the contribution is framed.
4. Rank limitations by (impact if solved) × (tractability) and mark the 3–5 live
   ones.

**Done when** there are ≥5 limitations with citations, each classified
fundamental/incidental, and the fallbacks table is filled. A limitation with no
source is a hypothesis and must be labeled `[unverified]`.

---

## 06-alignment — Align the idea with the limitations

**Goal.** The pipeline's decision point. Score the stage-01 idea against the
stage-05 limitations and decide: keep, sharpen, re-target, or pivot.

**Procedure.**
1. Build the alignment matrix: rows = live limitations, columns = does the idea
   address it (directly / partially / not), by what mechanism, and what evidence
   would prove it. Fill honestly; "partially" is the most common truthful answer.
2. For the best-matching limitation, run the **subsumption check**: search
   specifically for work that already applies this mechanism to this limitation
   (`LS search "<mechanism> for <limitation>" --tag 06-alignment`). If it exists,
   the idea is subsumed — say so, and locate the surviving delta.
3. Diagnose the mismatch type:
   - *Idea solves nothing live* → re-target to a limitation it does solve, or pivot.
   - *Idea solves an incidental limit* → reframe as an empirical/systems
     contribution with a strong evaluation, or raise ambition.
   - *Idea solves a fundamental limit but only under a strong assumption* → make
     the assumption the paper's scope, and defend it explicitly.
   - *Idea is subsumed* → report it; propose the nearest non-subsumed variant.
4. Write the **sharpened claim**: "For <setting>, <mechanism> removes <limitation>
   that <family> cannot, demonstrated by <benchmark + metric>."
5. Any outcome other than "keep, slightly sharpened" is a research-direction
   change — **present it to the user with the evidence and let them choose**
   before continuing to stage 07.

**Done when** the sharpened claim names a specific limitation from 05, a specific
mechanism from 04, and a specific benchmark from 03 — with the subsumption check
recorded (searched, what was found, why it doesn't subsume).

---

## 07-refine — Refinement into a paper skeleton

**Goal.** Turn the sharpened claim into the paper's load-bearing structure:
challenge → solution → benchmark triples, one per contribution.

**Procedure.**
1. Write 2–4 triples. Each is: **Challenge** (from 05, cited) → **Solution** (the
   mechanism component that addresses it) → **Benchmark** (the specific
   experiment, dataset, metric, and baseline that would demonstrate it), plus the
   **failure signal** — the result that would falsify this contribution.
   A triple that no experiment can falsify is not a contribution; drop it.
2. Check coverage: every contribution has an experiment; every experiment serves a
   contribution; every reviewer-obvious baseline appears. Delete orphans.
3. Write the paper skeleton (`templates.md` → skeleton): title candidates,
   abstract, per-section bullets with the argument each section must land, figure
   plan (Fig. 1 = the mechanism; Fig. 2 = the headline result), and the experiment
   table shells with columns filled and cells marked `TBD`.
4. Write the abstract and intro properly — they are the parts a reviewer actually
   reads, and writing them exposes a weak argument faster than any outline. Use
   the intro's four moves: the problem matters → what exists and where it stops
   (cite 05) → what we do → what we show.
5. Record the resource plan: what each experiment costs and what the user has.
6. Export `LS bib` and drop the draft into `draft/` (Markdown by default; add the
   LaTeX skeleton if the user names a venue with a template).

**Done when** every contribution is a falsifiable triple, the experiment table
shells exist, and the abstract + intro are written prose — not bullets.

---

## 08-evolve — Self-evolve

See `self-evolve.md`. In short: adversarial review rounds that score the draft,
generate concrete actions, **reopen earlier stages** (`PS reopen 02-related-work`)
to fix what they find, and repeat until the scorecard converges or the user stops.

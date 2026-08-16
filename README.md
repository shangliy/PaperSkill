# PaperSkill

A Claude Code skill that runs a research paper from raw idea to reviewed draft
through eight gated stages:

```
idea → related work → benchmarks → methodology → challenges/limitations
     → align idea with limitations → refine (challenge→solution→benchmark)
     → self-evolve (adversarial review rounds that reopen earlier stages)
```

Every stage writes a file, so the pipeline is resumable across sessions and each
claim is traceable to a source.

## Install

```bash
git clone https://github.com/shangliy/PaperSkill ~/.claude/skills/paper
```

Or, if you already have it checked out elsewhere:

```bash
ln -s /path/to/PaperSkill ~/.claude/skills/paper
```

Restart Claude Code, then say "I have a research idea: …" or invoke `/paper`.
Requires Python 3 (stdlib only) and network access for literature search.

## Layout

| Path | Role |
|------|------|
| `SKILL.md` | Dispatch, workspace layout, rules (loaded when the skill triggers) |
| `references/stage-guides.md` | Per-stage procedure, output contract, done-criteria |
| `references/templates.md` | Artifact skeletons for each stage + LaTeX skeleton |
| `references/self-evolve.md` | Reviewer personas, scorecard, convergence, escalation ladder |
| `scripts/paper_state.py` | Workspace init, stage gating, status, evolve rounds |
| `scripts/litsearch.py` | arXiv + OpenAlex + Semantic Scholar search, dedupe, bibtex |

## Scripts

Stdlib-only Python 3, no dependencies.

```bash
python3 scripts/paper_state.py init "Title" --root .        # → ./papers/<slug>/
python3 scripts/paper_state.py status --root .
python3 scripts/paper_state.py complete 02-related-work --summary "..." --root .
python3 scripts/paper_state.py reopen 03-benchmarks --root .   # self-evolve feedback edge
python3 scripts/paper_state.py round --root .                  # next review round

python3 scripts/litsearch.py search "query" --tag 02-related-work --workspace <ws>
python3 scripts/litsearch.py list --tag 03-benchmarks --workspace <ws>
python3 scripts/litsearch.py bib --workspace <ws>            # → refs.bib
```

Optional env: `PAPER_SKILL_EMAIL` (polite OpenAlex access), `S2_API_KEY`
(higher Semantic Scholar rate limit).

**Rate limits.** arXiv returns HTTP 429 to some shared/cloud IPs regardless of
pacing; the tool warns and continues on the remaining sources, and both OpenAlex
and Semantic Scholar index arXiv preprints, so coverage survives. If *all*
sources fail the command exits 2 — wait ~30s and retry.

## Design notes

- **Files over context.** Stage state lives in `state.json` and artifacts on
  disk, so a later session resumes exactly where the last one stopped.
- **One corpus.** All stages cite from `library.json`; `refs.bib` is generated
  from it, so the bibliography cannot drift from what was actually read.
- **The idea can lose.** Stage 06 explicitly allows the conclusion that the idea
  is subsumed by prior work, and stage 08 escalates to the user rather than
  quietly re-scoping.
- **Feedback edges, not a checklist.** Self-evolve rounds reopen stages 02–07;
  that loop is the "self-evolve" part of the pipeline.

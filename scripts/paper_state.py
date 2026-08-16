#!/usr/bin/env python3
"""Workspace + stage state for the paper pipeline. Stdlib only.

Commands:
  init "<title>" [--root DIR] [--slug S] [--venue V] [--domain D]
  status [--root DIR] [--workspace WS] [--json]
  complete <stage-id> [--summary TEXT]
  reopen <stage-id>
  note <text> [--stage ID]
  set <key> <value>            # meta fields: venue, domain, deadline, claim, ...
  round [--verdict TEXT]       # opens the next self-evolve round file
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

STAGES = [
    ("01-idea", "Idea intake", "01-idea.md"),
    ("02-related-work", "Related work", "02-related-work.md"),
    ("03-benchmarks", "Benchmarks", "03-benchmarks.md"),
    ("04-methodology", "Methodology", "04-methodology.md"),
    ("05-challenges", "Challenges & limitations", "05-challenges.md"),
    ("06-alignment", "Idea/limitation alignment", "06-alignment.md"),
    ("07-refine", "Refinement & paper skeleton", "07-refine.md"),
    ("08-evolve", "Self-evolve rounds", "08-evolve/"),
]
STAGE_IDS = [s[0] for s in STAGES]


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(s) > 48:  # trim on a word boundary, not mid-word
        s = s[:48].rsplit("-", 1)[0]
    return s or "paper"


def find_workspace(root, explicit=None):
    """Explicit path wins; else the most recently updated workspace under root."""
    if explicit:
        ws = os.path.abspath(explicit)
        if not os.path.isfile(os.path.join(ws, "state.json")):
            die("no state.json in %s (run `init` first)" % ws)
        return ws
    candidates = []
    for base in (os.path.join(root, "papers"), root):
        if not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            p = os.path.join(base, name, "state.json")
            if os.path.isfile(p):
                candidates.append((os.path.getmtime(p), os.path.dirname(p)))
        if os.path.isfile(os.path.join(base, "state.json")):
            candidates.append((os.path.getmtime(os.path.join(base, "state.json")), base))
    if not candidates:
        return None
    return sorted(candidates)[-1][1]


def die(msg):
    print("error: %s" % msg, file=sys.stderr)
    sys.exit(1)


def load(ws):
    with open(os.path.join(ws, "state.json")) as f:
        return json.load(f)


def save(ws, state):
    state["updated"] = now()
    with open(os.path.join(ws, "state.json"), "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


def log(state, event):
    state.setdefault("log", []).append({"ts": now(), "event": event})


def resolve(root, explicit):
    ws = find_workspace(root, explicit)
    if not ws:
        die("no paper workspace found under %s — run `init \"<title>\"` first" % root)
    return ws


# --------------------------------------------------------------------------- init

STUB = """# {title}

> Stage: {stage} — status: TODO
> Fill this in by following `references/stage-guides.md` (section {sid}).
"""


def cmd_init(args):
    root = os.path.abspath(args.root)
    slug = args.slug or slugify(args.title)
    ws = os.path.join(root, "papers", slug)
    if os.path.isfile(os.path.join(ws, "state.json")):
        die("workspace already exists: %s (use `status` to resume)" % ws)
    os.makedirs(os.path.join(ws, "08-evolve"), exist_ok=True)
    os.makedirs(os.path.join(ws, "draft"), exist_ok=True)
    state = {
        "slug": slug,
        "title": args.title,
        "created": now(),
        "updated": now(),
        "meta": {
            "domain": args.domain or "",
            "venue": args.venue or "",
            "deadline": "",
            "claim": "",
        },
        "stages": {
            sid: {"status": "todo", "summary": "", "updated": ""} for sid in STAGE_IDS
        },
        "rounds": 0,
        "log": [],
    }
    for sid, name, path in STAGES:
        if path.endswith("/"):
            continue
        fp = os.path.join(ws, path)
        if not os.path.exists(fp):
            with open(fp, "w") as f:
                f.write(STUB.format(title=name, stage=name, sid=sid))
    with open(os.path.join(ws, "library.json"), "w") as f:
        json.dump({"entries": [], "queries": []}, f, indent=2)
    log(state, "init %s" % slug)
    save(ws, state)
    print("workspace: %s" % ws)
    print("next stage: 01-idea  (see references/stage-guides.md)")


# ------------------------------------------------------------------------- status

MARK = {"done": "[x]", "active": "[~]", "todo": "[ ]", "blocked": "[!]"}


def cmd_status(args):
    ws = resolve(os.path.abspath(args.root), args.workspace)
    state = load(ws)
    if args.json:
        state["workspace"] = ws
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return
    lib = {"entries": []}
    libp = os.path.join(ws, "library.json")
    if os.path.isfile(libp):
        with open(libp) as f:
            lib = json.load(f)
    print("%s  (%s)" % (state["title"], state["slug"]))
    print("workspace: %s" % ws)
    meta = {k: v for k, v in state.get("meta", {}).items() if v}
    if meta:
        print("meta: " + "  ".join("%s=%s" % (k, v) for k, v in meta.items()))
    print("library: %d papers | evolve rounds: %d" % (len(lib.get("entries", [])), state.get("rounds", 0)))
    print()
    nxt = None
    for sid, name, _ in STAGES:
        st = state["stages"].get(sid, {})
        status = st.get("status", "todo")
        line = "%s %-16s %-26s" % (MARK.get(status, "[ ]"), sid, name)
        if st.get("summary"):
            line += " — " + st["summary"]
        print(line)
        if nxt is None and status in ("todo", "active", "blocked"):
            nxt = sid
    print()
    print("next: %s" % (nxt or "all stages complete — run `round` for another self-evolve pass"))
    notes = [e for e in state.get("log", []) if e["event"].startswith("note:")]
    if notes:
        print("\nrecent notes:")
        for e in notes[-5:]:
            print("  - %s" % e["event"][5:].strip())


# ------------------------------------------------------------------- mutate stages


def cmd_complete(args):
    ws = resolve(os.path.abspath(args.root), args.workspace)
    state = load(ws)
    if args.stage not in state["stages"]:
        die("unknown stage %r (expected one of: %s)" % (args.stage, ", ".join(STAGE_IDS)))
    state["stages"][args.stage].update(
        {"status": "done", "summary": args.summary or "", "updated": now()}
    )
    log(state, "complete %s" % args.stage)
    save(ws, state)
    remaining = [s for s in STAGE_IDS if state["stages"][s]["status"] != "done"]
    print("%s → done" % args.stage)
    print("next: %s" % (remaining[0] if remaining else "all complete"))


def cmd_reopen(args):
    ws = resolve(os.path.abspath(args.root), args.workspace)
    state = load(ws)
    if args.stage not in state["stages"]:
        die("unknown stage %r" % args.stage)
    state["stages"][args.stage].update({"status": "active", "updated": now()})
    log(state, "reopen %s (%s)" % (args.stage, args.summary or "self-evolve feedback"))
    save(ws, state)
    print("%s → active" % args.stage)


def cmd_note(args):
    ws = resolve(os.path.abspath(args.root), args.workspace)
    state = load(ws)
    prefix = "[%s] " % args.stage if args.stage else ""
    log(state, "note: %s%s" % (prefix, args.text))
    save(ws, state)
    print("noted")


def cmd_set(args):
    ws = resolve(os.path.abspath(args.root), args.workspace)
    state = load(ws)
    state.setdefault("meta", {})[args.key] = args.value
    log(state, "set %s=%s" % (args.key, args.value))
    save(ws, state)
    print("%s = %s" % (args.key, args.value))


ROUND_STUB = """# Self-evolve round {n}

_Opened {ts}. Procedure: `references/self-evolve.md`._

## Scorecard (1-5)

| Axis | Score | Evidence |
|------|-------|----------|
| Novelty |  |  |
| Significance |  |  |
| Soundness |  |  |
| Evaluation fit |  |  |
| Clarity |  |  |

## Reviewer findings

## Actions (stage → what to redo)

## Verdict
{verdict}
"""


def cmd_round(args):
    ws = resolve(os.path.abspath(args.root), args.workspace)
    state = load(ws)
    n = state.get("rounds", 0) + 1
    state["rounds"] = n
    state["stages"]["08-evolve"]["status"] = "active"
    state["stages"]["08-evolve"]["updated"] = now()
    os.makedirs(os.path.join(ws, "08-evolve"), exist_ok=True)
    fp = os.path.join(ws, "08-evolve", "round-%d.md" % n)
    if not os.path.exists(fp):
        with open(fp, "w") as f:
            f.write(ROUND_STUB.format(n=n, ts=now(), verdict=args.verdict or ""))
    log(state, "open evolve round %d" % n)
    save(ws, state)
    print("round %d: %s" % (n, fp))


def main():
    # --root/--workspace are accepted both before and after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=None, help="project root (workspaces live in <root>/papers/)")
    common.add_argument("--workspace", default=None, help="explicit workspace dir; otherwise the most recent one")

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", dest="root_pre", default=None, help=argparse.SUPPRESS)
    p.add_argument("--workspace", dest="workspace_pre", default=None, help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name):
        return sub.add_parser(name, parents=[common])

    a = add("init"); a.add_argument("title"); a.add_argument("--slug")
    a.add_argument("--venue"); a.add_argument("--domain"); a.set_defaults(fn=cmd_init)

    a = add("status"); a.add_argument("--json", action="store_true"); a.set_defaults(fn=cmd_status)

    a = add("complete"); a.add_argument("stage"); a.add_argument("--summary"); a.set_defaults(fn=cmd_complete)
    a = add("reopen"); a.add_argument("stage"); a.add_argument("--summary"); a.set_defaults(fn=cmd_reopen)
    a = add("note"); a.add_argument("text"); a.add_argument("--stage"); a.set_defaults(fn=cmd_note)
    a = add("set"); a.add_argument("key"); a.add_argument("value"); a.set_defaults(fn=cmd_set)
    a = add("round"); a.add_argument("--verdict"); a.set_defaults(fn=cmd_round)

    args = p.parse_args()
    args.root = args.root or args.root_pre or "."
    args.workspace = args.workspace or args.workspace_pre
    args.fn(args)


if __name__ == "__main__":
    main()

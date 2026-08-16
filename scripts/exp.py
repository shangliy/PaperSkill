#!/usr/bin/env python3
"""Experiment registry, run log, and statistics for the paper pipeline.

Stdlib only. Two files in the workspace:
  experiments.json   pre-registered protocols, the change ledger, test-eval budget
  results/runs.jsonl append-only run log (one JSON object per run)

Pre-registration is not bureaucracy: registering the metric, seeds, and success
threshold *before* running is what separates a result from a story told after
the fact.

  register <name> --hypothesis H --metric acc --dataset D --seeds N --success "..."
  log <name> --metric acc=0.83 --seed 1 [--split dev|test] [--config k=v] [--notes ...]
  runs [name] [--json]
  table --metric acc [--split dev]
  compare <baseline> <candidate> --metric acc [--split dev] [--alpha 0.05]
  attempt --round N --change "..." --predicted "..." --observed "..." --verdict accept|reject
  ledger | status
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys
from datetime import datetime
from itertools import combinations

DEFAULT_TEST_BUDGET = 5


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def die(msg):
    print("error: %s" % msg, file=sys.stderr)
    sys.exit(1)


def reg_path(ws):
    return os.path.join(ws, "experiments.json")


def runs_path(ws):
    return os.path.join(ws, "results", "runs.jsonl")


def load_reg(ws):
    p = reg_path(ws)
    if os.path.isfile(p):
        with open(p) as f:
            return json.load(f)
    return {"protocols": {}, "ledger": [], "test_budget": DEFAULT_TEST_BUDGET, "test_evals": 0}


def save_reg(ws, reg):
    os.makedirs(ws, exist_ok=True)
    with open(reg_path(ws), "w") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_runs(ws):
    p = runs_path(ws)
    if not os.path.isfile(p):
        return []
    out = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def append_run(ws, rec):
    os.makedirs(os.path.dirname(runs_path(ws)), exist_ok=True)
    with open(runs_path(ws), "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def kv(pairs, cast=False):
    d = {}
    for item in pairs or []:
        if "=" not in item:
            die("expected key=value, got %r" % item)
        k, v = item.split("=", 1)
        if cast:
            try:
                v = float(v)
            except ValueError:
                die("metric %r must be numeric, got %r" % (k, v))
        d[k.strip()] = v
    return d


# ------------------------------------------------------------------ statistics


def mean(xs):
    return sum(xs) / len(xs)


def stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def cohens_d(a, b):
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    sp = math.sqrt(((na - 1) * stdev(a) ** 2 + (nb - 1) * stdev(b) ** 2) / (na + nb - 2))
    return (mean(b) - mean(a)) / sp if sp else float("inf")


def perm_test(a, b, iters=20000, seed=0):
    """Two-sided permutation test on the difference of means.

    Exact when the number of splits is small — which it always is at the seed
    counts papers actually use. Returns (p, mode, min_achievable_p).
    """
    obs = abs(mean(b) - mean(a))
    pool = list(a) + list(b)
    na, n = len(a), len(a) + len(b)
    total = math.comb(n, na)
    min_p = 2.0 / total if total else 1.0
    if total <= iters:
        hits = 0
        for idx in combinations(range(n), na):
            s = set(idx)
            A = [pool[i] for i in idx]
            B = [pool[i] for i in range(n) if i not in s]
            if abs(mean(B) - mean(A)) >= obs - 1e-12:
                hits += 1
        return hits / total, "exact", min_p
    rnd = random.Random(seed)
    hits = 0
    for _ in range(iters):
        p = pool[:]
        rnd.shuffle(p)
        if abs(mean(p[na:]) - mean(p[:na])) >= obs - 1e-12:
            hits += 1
    return hits / iters, "monte-carlo(%d)" % iters, min_p


def bootstrap_ci(xs, alpha=0.05, iters=5000, seed=0):
    if len(xs) < 2:
        return (float("nan"), float("nan"))
    rnd = random.Random(seed)
    ms = sorted(mean([rnd.choice(xs) for _ in xs]) for _ in range(iters))
    lo = ms[int((alpha / 2) * iters)]
    hi = ms[min(iters - 1, int((1 - alpha / 2) * iters))]
    return (lo, hi)


# -------------------------------------------------------------------- commands


def cmd_register(args):
    ws = os.path.abspath(args.workspace)
    reg = load_reg(ws)
    if args.name in reg["protocols"] and not args.force:
        die("protocol %r already registered (--force to overwrite; overwriting a "
            "protocol after seeing results is exactly what pre-registration prevents)" % args.name)
    reg["protocols"][args.name] = {
        "name": args.name,
        "hypothesis": args.hypothesis,
        "metrics": [m.strip() for m in args.metric.split(",")],
        "dataset": args.dataset,
        "split_policy": args.split_policy,
        "seeds": args.seeds,
        "success": args.success,
        "contribution": args.contribution or "",
        "registered": now(),
        "commit": args.commit or git_commit(),
    }
    if args.test_budget is not None:
        reg["test_budget"] = args.test_budget
    save_reg(ws, reg)
    print("registered %s" % args.name)
    print("  hypothesis: %s" % args.hypothesis)
    print("  success:    %s" % args.success)
    print("  metrics:    %s | dataset: %s | seeds: %d" % (args.metric, args.dataset, args.seeds))


def cmd_log(args):
    ws = os.path.abspath(args.workspace)
    reg = load_reg(ws)
    metrics = kv(args.metric, cast=True)
    if not metrics:
        die("at least one --metric key=value is required")
    if args.name not in reg["protocols"] and not args.unregistered:
        die("no protocol %r — `register` it first, or pass --unregistered for an "
            "exploratory run (it will be excluded from paper tables)" % args.name)
    rec = {
        "ts": now(),
        "name": args.name,
        "split": args.split,
        "seed": args.seed,
        "metrics": metrics,
        "config": kv(args.config),
        "commit": args.commit or git_commit(),
        "cost": args.cost or "",
        "notes": args.notes or "",
        "registered": args.name in reg["protocols"],
    }
    append_run(ws, rec)
    msg = "logged %s seed=%s split=%s %s" % (
        args.name, args.seed, args.split,
        " ".join("%s=%.4g" % (k, v) for k, v in metrics.items()))
    if args.split == "test":
        reg["test_evals"] = reg.get("test_evals", 0) + 1
        save_reg(ws, reg)
        left = reg.get("test_budget", DEFAULT_TEST_BUDGET) - reg["test_evals"]
        msg += "\ntest-set evaluations used: %d/%d" % (reg["test_evals"], reg.get("test_budget", DEFAULT_TEST_BUDGET))
        if left <= 0:
            msg += "\nBUDGET EXCEEDED — every extra test eval erodes the number's meaning. Tune on dev."
        elif left <= 2:
            msg += "  (%d left)" % left
    print(msg)


def group_runs(runs, metric, split=None, names=None):
    """→ {name: [values]} for one metric, keeping seed order."""
    out = {}
    for r in runs:
        if split and r.get("split") != split:
            continue
        if names and r["name"] not in names:
            continue
        if metric not in r.get("metrics", {}):
            continue
        out.setdefault(r["name"], []).append(r["metrics"][metric])
    return out


def cmd_runs(args):
    ws = os.path.abspath(args.workspace)
    runs = load_runs(ws)
    if args.name:
        runs = [r for r in runs if r["name"] == args.name]
    if args.json:
        print(json.dumps(runs, indent=2, ensure_ascii=False))
        return
    if not runs:
        print("no runs logged yet")
        return
    for r in runs:
        print("%s  %-22s %-5s seed=%-4s %s  %s%s" % (
            r["ts"][:16], r["name"], r["split"], r["seed"],
            " ".join("%s=%.4g" % (k, v) for k, v in r["metrics"].items()),
            r.get("commit", ""), "" if r.get("registered", True) else "  [unregistered]"))


def cmd_table(args):
    ws = os.path.abspath(args.workspace)
    runs = load_runs(ws)
    groups = group_runs(runs, args.metric, args.split)
    if not groups:
        print("no runs with metric %r%s" % (args.metric, " on split %s" % args.split if args.split else ""))
        return
    print("| Run | n seeds | %s (mean ± sd) | 95%% CI | min | max |" % args.metric)
    print("|---|---|---|---|---|---|")
    for name, vals in sorted(groups.items(), key=lambda kv2: -mean(kv2[1])):
        lo, hi = bootstrap_ci(vals)
        ci = "[%.4g, %.4g]" % (lo, hi) if len(vals) > 1 else "—"
        print("| %s | %d | %.4g ± %.4g | %s | %.4g | %.4g |" % (
            name, len(vals), mean(vals), stdev(vals), ci, min(vals), max(vals)))
    single = [n for n, v in groups.items() if len(v) < 3]
    if single:
        print("\n> single/low-seed runs (n<3), not reportable as results: %s" % ", ".join(single))


def cmd_compare(args):
    ws = os.path.abspath(args.workspace)
    runs = load_runs(ws)
    g = group_runs(runs, args.metric, args.split, names=[args.baseline, args.candidate])
    a, b = g.get(args.baseline), g.get(args.candidate)
    if not a or not b:
        die("need runs for both %r (%d) and %r (%d) with metric %r%s"
            % (args.baseline, len(a or []), args.candidate, len(b or []), args.metric,
               " on split %s" % args.split if args.split else ""))
    delta = mean(b) - mean(a)
    noise = max(stdev(a), stdev(b))
    p, mode, min_p = perm_test(a, b)
    d = cohens_d(a, b)
    print("metric: %s%s" % (args.metric, "  split: %s" % args.split if args.split else ""))
    print("  %-24s %.4g ± %.4g  (n=%d)" % (args.baseline, mean(a), stdev(a), len(a)))
    print("  %-24s %.4g ± %.4g  (n=%d)" % (args.candidate, mean(b), stdev(b), len(b)))
    rel = (delta / mean(a) * 100) if mean(a) else float("nan")
    print("  delta: %+.4g (%+.2f%%)   seed-noise band: %.4g   Cohen's d: %.2f" % (delta, rel, noise, d))
    print("  permutation p = %.4g (%s)" % (p, mode))
    if min_p > args.alpha:
        print("  NOTE: with n=%d/%d the smallest achievable p is %.3g — no result at these seed "
              "counts can reach alpha=%.3g. Run more seeds before claiming significance."
              % (len(a), len(b), min_p, args.alpha))
    if delta <= 0:
        verdict = "REJECT — candidate does not beat baseline"
    elif abs(delta) < noise:
        verdict = "REJECT — gain is inside the seed-noise band; this is not an improvement"
    elif p > args.alpha:
        verdict = "INCONCLUSIVE — gain exceeds noise but p=%.3g > alpha; add seeds" % p
    else:
        verdict = "ACCEPT — gain exceeds noise and p < alpha"
    print("  verdict: %s" % verdict)
    if args.json:
        print(json.dumps({"baseline": args.baseline, "candidate": args.candidate,
                          "metric": args.metric, "delta": delta, "p": p, "d": d,
                          "noise": noise, "verdict": verdict.split(" —")[0]}, indent=2))


def cmd_attempt(args):
    ws = os.path.abspath(args.workspace)
    reg = load_reg(ws)
    reg.setdefault("ledger", []).append({
        "ts": now(), "round": args.round, "change": args.change,
        "predicted": args.predicted or "", "observed": args.observed or "",
        "verdict": args.verdict, "kept": args.verdict == "accept",
        "notes": args.notes or "",
    })
    save_reg(ws, reg)
    n = len(reg["ledger"])
    kept = sum(1 for e in reg["ledger"] if e["kept"])
    print("attempt #%d recorded (%s). kept %d/%d changes." % (n, args.verdict, kept, n))


def cmd_ledger(args):
    ws = os.path.abspath(args.workspace)
    reg = load_reg(ws)
    entries = reg.get("ledger", [])
    if not entries:
        print("ledger empty — no improvement attempts recorded yet")
        return
    print("| # | Round | Change | Predicted | Observed | Verdict |")
    print("|---|---|---|---|---|---|")
    for i, e in enumerate(entries, 1):
        print("| %d | %s | %s | %s | %s | %s |" % (
            i, e.get("round", ""), e["change"], e.get("predicted", ""),
            e.get("observed", ""), e["verdict"]))
    kept = sum(1 for e in entries if e["kept"])
    print("\n%d attempts, %d kept, %d rejected. Rejected attempts belong in the paper's "
          "ablation/limitations discussion — they are evidence, not waste."
          % (len(entries), kept, len(entries) - kept))


def cmd_status(args):
    ws = os.path.abspath(args.workspace)
    reg, runs = load_reg(ws), load_runs(ws)
    protos = reg.get("protocols", {})
    print("protocols: %d | runs: %d | attempts: %d" % (len(protos), len(runs), len(reg.get("ledger", []))))
    budget, used = reg.get("test_budget", DEFAULT_TEST_BUDGET), reg.get("test_evals", 0)
    print("test-set evaluations: %d/%d%s" % (used, budget, "  OVER BUDGET" if used > budget else ""))
    for name, pr in protos.items():
        seen = [r for r in runs if r["name"] == name]
        seeds = sorted({r["seed"] for r in seen if r["seed"] is not None})
        state = "no runs" if not seen else "%d runs, seeds %s" % (len(seen), seeds)
        need = pr.get("seeds", 0)
        flag = "" if len(seeds) >= need else "  (needs %d seeds)" % need
        print("  %-24s %s%s" % (name, state, flag))
        print("      success: %s" % pr.get("success", ""))


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workspace", default=None, help="paper workspace dir")

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--workspace", dest="workspace_pre", default=None, help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("register", parents=[common])
    a.add_argument("name")
    a.add_argument("--hypothesis", required=True)
    a.add_argument("--metric", required=True, help="comma-separated metric names")
    a.add_argument("--dataset", required=True)
    a.add_argument("--seeds", type=int, default=3)
    a.add_argument("--success", required=True, help="threshold decided BEFORE running")
    a.add_argument("--split-policy", default="tune on dev, test once at the end")
    a.add_argument("--contribution", help="which 07-refine triple this serves")
    a.add_argument("--test-budget", type=int)
    a.add_argument("--commit")
    a.add_argument("--force", action="store_true")
    a.set_defaults(fn=cmd_register)

    a = sub.add_parser("log", parents=[common])
    a.add_argument("name")
    a.add_argument("--metric", action="append", required=True, help="key=value (repeatable)")
    a.add_argument("--seed", type=int)
    a.add_argument("--split", default="dev", choices=["train", "dev", "test"])
    a.add_argument("--config", action="append", help="key=value (repeatable)")
    a.add_argument("--commit")
    a.add_argument("--cost", help="e.g. '2.5 GPU-h'")
    a.add_argument("--notes")
    a.add_argument("--unregistered", action="store_true")
    a.set_defaults(fn=cmd_log)

    a = sub.add_parser("runs", parents=[common])
    a.add_argument("name", nargs="?")
    a.add_argument("--json", action="store_true")
    a.set_defaults(fn=cmd_runs)

    a = sub.add_parser("table", parents=[common])
    a.add_argument("--metric", required=True)
    a.add_argument("--split")
    a.set_defaults(fn=cmd_table)

    a = sub.add_parser("compare", parents=[common])
    a.add_argument("baseline")
    a.add_argument("candidate")
    a.add_argument("--metric", required=True)
    a.add_argument("--split")
    a.add_argument("--alpha", type=float, default=0.05)
    a.add_argument("--json", action="store_true")
    a.set_defaults(fn=cmd_compare)

    a = sub.add_parser("attempt", parents=[common])
    a.add_argument("--round", type=int)
    a.add_argument("--change", required=True)
    a.add_argument("--predicted")
    a.add_argument("--observed")
    a.add_argument("--verdict", required=True, choices=["accept", "reject", "inconclusive"])
    a.add_argument("--notes")
    a.set_defaults(fn=cmd_attempt)

    a = sub.add_parser("ledger", parents=[common]); a.set_defaults(fn=cmd_ledger)
    a = sub.add_parser("status", parents=[common]); a.set_defaults(fn=cmd_status)

    args = p.parse_args()
    args.workspace = args.workspace or args.workspace_pre or "."
    args.fn(args)


if __name__ == "__main__":
    main()

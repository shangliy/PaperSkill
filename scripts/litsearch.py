#!/usr/bin/env python3
"""Literature retrieval for the paper pipeline: arXiv + OpenAlex + Semantic Scholar.

Stdlib only. Results are deduped by normalized title and persisted to
<workspace>/library.json so every stage cites the same corpus.

  search "query" [--tag STAGE] [--limit N] [--year-min Y] [--source arxiv,openalex,s2]
  list [--tag STAGE] [--sort year|citations] [--json]
  show <key>
  bib [--out refs.bib]

Set PAPER_SKILL_EMAIL for polite OpenAlex/Crossref access; S2_API_KEY is used
for Semantic Scholar if present (higher rate limit, not required).
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

EMAIL = os.environ.get("PAPER_SKILL_EMAIL", "paper-skill@example.com")
UA = "PaperSkill/1.0 (mailto:%s)" % EMAIL
SOURCES = ("arxiv", "openalex", "s2")


def warn(msg):
    print("warn: %s" % msg, file=sys.stderr)


def fetch(url, headers=None, timeout=45, retries=2):
    hdr = {"User-Agent": UA, "Accept": "application/json"}
    hdr.update(headers or {})
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=hdr)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(4 * (attempt + 1))  # arXiv/S2 rate limits want seconds, not ms
                continue
            break
        except Exception as e:  # network down, DNS, timeout
            last = e
            if attempt < retries:
                time.sleep(1 + attempt)
                continue
            break
    raise last


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


# ------------------------------------------------------------------- providers


def search_arxiv(query, limit, year_min):
    q = urllib.parse.quote('all:"%s"' % query)
    url = ("https://export.arxiv.org/api/query?search_query=%s&start=0"
           "&max_results=%d&sortBy=relevance&sortOrder=descending" % (q, limit))
    raw = fetch(url, headers={"Accept": "application/atom+xml"})
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(raw).findall("a:entry", ns):
        eid = clean(e.findtext("a:id", "", ns))
        aid = eid.rsplit("/abs/", 1)[-1]
        published = clean(e.findtext("a:published", "", ns))
        year = int(published[:4]) if published[:4].isdigit() else None
        if year_min and year and year < year_min:
            continue
        doi = e.findtext("{http://arxiv.org/schemas/atom}doi")
        out.append({
            "title": clean(e.findtext("a:title", "", ns)),
            "authors": [clean(a.findtext("a:name", "", ns)) for a in e.findall("a:author", ns)],
            "year": year,
            "venue": clean(e.findtext("{http://arxiv.org/schemas/atom}journal_ref") or "arXiv preprint"),
            "abstract": clean(e.findtext("a:summary", "", ns)),
            "url": eid,
            "doi": clean(doi) if doi else "",
            "arxiv_id": aid,
            "citations": None,
            "source": "arxiv",
        })
    return out


def _openalex_abstract(inv):
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return clean(" ".join(pos[i] for i in sorted(pos)))


def search_openalex(query, limit, year_min):
    params = {"search": query, "per-page": str(min(limit, 50)), "mailto": EMAIL}
    if year_min:
        params["filter"] = "from_publication_date:%d-01-01" % year_min
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    data = json.loads(fetch(url))
    out = []
    for w in data.get("results", []):
        pl = w.get("primary_location") or {}
        src = (pl.get("source") or {}).get("display_name") or ""
        ids = w.get("ids", {})
        arxiv_id = ""
        for cand in (pl.get("landing_page_url") or "", ids.get("doi") or ""):
            m = re.search(r"arxiv\.org/abs/([\w.\-/]+)", cand)
            if m:
                arxiv_id = m.group(1)
        out.append({
            "title": clean(w.get("display_name")),
            "authors": [clean((a.get("author") or {}).get("display_name"))
                        for a in (w.get("authorships") or [])[:12]],
            "year": w.get("publication_year"),
            "venue": clean(src),
            "abstract": _openalex_abstract(w.get("abstract_inverted_index")),
            "url": pl.get("landing_page_url") or ids.get("doi") or w.get("id", ""),
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "arxiv_id": arxiv_id,
            "citations": w.get("cited_by_count"),
            "source": "openalex",
        })
    return out


def search_s2(query, limit, year_min):
    fields = "title,abstract,year,venue,citationCount,externalIds,authors,url"
    params = {"query": query, "limit": str(min(limit, 100)), "fields": fields}
    if year_min:
        params["year"] = "%d-" % year_min
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(params)
    headers = {}
    if os.environ.get("S2_API_KEY"):
        headers["x-api-key"] = os.environ["S2_API_KEY"]
    data = json.loads(fetch(url, headers=headers))
    out = []
    for p in data.get("data", []):
        ext = p.get("externalIds") or {}
        out.append({
            "title": clean(p.get("title")),
            "authors": [clean(a.get("name")) for a in (p.get("authors") or [])[:12]],
            "year": p.get("year"),
            "venue": clean(p.get("venue")),
            "abstract": clean(p.get("abstract")),
            "url": p.get("url") or "",
            "doi": ext.get("DOI", "") or "",
            "arxiv_id": ext.get("ArXiv", "") or "",
            "citations": p.get("citationCount"),
            "source": "s2",
        })
    return out


PROVIDERS = {"arxiv": search_arxiv, "openalex": search_openalex, "s2": search_s2}


# --------------------------------------------------------------------- library


def lib_path(ws):
    return os.path.join(ws, "library.json")


def load_lib(ws):
    p = lib_path(ws)
    if os.path.isfile(p):
        with open(p) as f:
            return json.load(f)
    return {"entries": [], "queries": []}


def save_lib(ws, lib):
    os.makedirs(ws, exist_ok=True)
    with open(lib_path(ws), "w") as f:
        json.dump(lib, f, indent=2, ensure_ascii=False)
        f.write("\n")


def cite_key(rec, taken):
    first = (rec["authors"][0] if rec.get("authors") else "anon").split()[-1]
    first = re.sub(r"[^A-Za-z]", "", first).lower() or "anon"
    word = next((w for w in re.findall(r"[A-Za-z]{4,}", rec.get("title", ""))), "work").lower()
    base = "%s%s%s" % (first, rec.get("year") or "nd", word)
    key, n = base, 1
    while key in taken:
        n += 1
        key = "%s%d" % (base, n)
    return key


def merge(lib, records, tag, query):
    """Merge by normalized title; richer field wins, tags/sources accumulate."""
    index = {norm_title(e["title"]): e for e in lib["entries"] if e.get("title")}
    taken = {e["key"] for e in lib["entries"]}
    added, updated = [], 0
    for rec in records:
        nt = norm_title(rec.get("title"))
        if not nt:
            continue
        cur = index.get(nt)
        if cur:
            for k, v in rec.items():
                if v and not cur.get(k):
                    cur[k] = v
            if rec["source"] not in cur.setdefault("sources", [cur.get("source", "")]):
                cur["sources"].append(rec["source"])
            if tag and tag not in cur.setdefault("tags", []):
                cur["tags"].append(tag)
            if query not in cur.setdefault("queries", []):
                cur["queries"].append(query)
            updated += 1
            continue
        rec["key"] = cite_key(rec, taken)
        taken.add(rec["key"])
        rec["sources"] = [rec["source"]]
        rec["tags"] = [tag] if tag else []
        rec["queries"] = [query]
        rec["notes"] = ""
        lib["entries"].append(rec)
        index[nt] = rec
        added.append(rec)
    return added, updated


def fmt(rec, abstract=False):
    au = rec.get("authors") or []
    who = au[0] + (" et al." if len(au) > 1 else "") if au else "?"
    cites = rec.get("citations")
    line = "  [%s] %s (%s, %s)%s\n      %s" % (
        rec["key"], who, rec.get("year") or "n.d.", rec.get("venue") or "?",
        "  cites=%s" % cites if cites is not None else "", rec.get("title", ""))
    if rec.get("url"):
        line += "\n      %s" % rec["url"]
    if abstract and rec.get("abstract"):
        line += "\n      %s" % rec["abstract"][:400]
    return line


# ---------------------------------------------------------------------- commands


def cmd_search(args):
    ws = os.path.abspath(args.workspace)
    sources = [s.strip() for s in args.source.split(",") if s.strip()]
    bad = [s for s in sources if s not in PROVIDERS]
    if bad:
        print("error: unknown source(s): %s (valid: %s)" % (", ".join(bad), ", ".join(SOURCES)),
              file=sys.stderr)
        sys.exit(1)
    lib = load_lib(ws)
    records, ok, failed = [], [], []
    for i, name in enumerate(sources):
        if i:
            time.sleep(args.sleep)  # arXiv and S2 rate-limit bursts hard
        try:
            got = PROVIDERS[name](args.query, args.limit, args.year_min)
            records.extend(got)
            ok.append("%s:%d" % (name, len(got)))
        except Exception as e:
            failed.append(name)
            warn("%s failed: %s" % (name, e))
    if failed and not ok:
        print("all sources failed (%s) — usually a transient 429; wait ~30s and retry, "
              "or narrow with --source" % ", ".join(failed), file=sys.stderr)
        sys.exit(2)
    if not records:
        print("no results (sources tried: %s)" % ", ".join(ok))
        return
    added, updated = merge(lib, records, args.tag, args.query)
    lib.setdefault("queries", []).append(
        {"query": args.query, "tag": args.tag or "", "sources": ok, "new": len(added)})
    save_lib(ws, lib)
    print("query: %s   [%s]  → %d new, %d enriched, %d in library"
          % (args.query, " ".join(ok), len(added), updated, len(lib["entries"])))
    for rec in sorted(added, key=lambda r: -(r.get("citations") or 0)):
        print(fmt(rec, abstract=args.abstracts))
    if not added:
        print("  (all results already in library)")


def cmd_list(args):
    lib = load_lib(os.path.abspath(args.workspace))
    entries = lib["entries"]
    if args.tag:
        entries = [e for e in entries if args.tag in e.get("tags", [])]
    keyf = {"year": lambda e: -(e.get("year") or 0),
            "citations": lambda e: -(e.get("citations") or 0),
            "key": lambda e: e["key"]}[args.sort]
    entries = sorted(entries, key=keyf)
    if args.json:
        print(json.dumps(entries, indent=2, ensure_ascii=False))
        return
    print("%d papers%s" % (len(entries), " tagged %s" % args.tag if args.tag else ""))
    for e in entries:
        print(fmt(e, abstract=args.abstracts))


def cmd_show(args):
    lib = load_lib(os.path.abspath(args.workspace))
    for e in lib["entries"]:
        if e["key"] == args.key:
            print(json.dumps(e, indent=2, ensure_ascii=False))
            return
    print("error: no entry with key %r" % args.key, file=sys.stderr)
    sys.exit(1)


def bib_escape(s):
    return clean(s).replace("{", "").replace("}", "").replace("\\", "")


def cmd_bib(args):
    ws = os.path.abspath(args.workspace)
    lib = load_lib(ws)
    out = []
    for e in sorted(lib["entries"], key=lambda r: r["key"]):
        etype = "article" if e.get("doi") and "arxiv" not in (e.get("venue") or "").lower() else "misc"
        fields = [("title", "{%s}" % bib_escape(e.get("title"))),
                  ("author", bib_escape(" and ".join(e.get("authors") or []))),
                  ("year", str(e.get("year") or "")),
                  ("journal" if etype == "article" else "howpublished", bib_escape(e.get("venue"))),
                  ("doi", e.get("doi") or ""),
                  ("eprint", e.get("arxiv_id") or ""),
                  ("url", e.get("url") or "")]
        body = ",\n".join("  %s = {%s}" % (k, v.strip("{}") if k == "title" else v)
                          for k, v in fields if v)
        out.append("@%s{%s,\n%s\n}" % (etype, e["key"], body))
    path = args.out if os.path.isabs(args.out) else os.path.join(ws, args.out)
    with open(path, "w") as f:
        f.write("\n\n".join(out) + "\n")
    print("wrote %d entries → %s" % (len(out), path))


def main():
    # --workspace is accepted both before and after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workspace", default=None, help="paper workspace dir (holds library.json)")

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--workspace", dest="workspace_pre", default=None, help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("search", parents=[common])
    a.add_argument("query")
    a.add_argument("--tag", help="stage id, e.g. 02-related-work")
    a.add_argument("--limit", type=int, default=20)
    a.add_argument("--year-min", type=int)
    a.add_argument("--source", default=",".join(SOURCES))
    a.add_argument("--abstracts", action="store_true")
    a.add_argument("--sleep", type=float, default=1.5, help="pause between providers (rate limits)")
    a.set_defaults(fn=cmd_search)

    a = sub.add_parser("list", parents=[common])
    a.add_argument("--tag")
    a.add_argument("--sort", choices=["year", "citations", "key"], default="citations")
    a.add_argument("--abstracts", action="store_true")
    a.add_argument("--json", action="store_true")
    a.set_defaults(fn=cmd_list)

    a = sub.add_parser("show", parents=[common]); a.add_argument("key"); a.set_defaults(fn=cmd_show)
    a = sub.add_parser("bib", parents=[common]); a.add_argument("--out", default="refs.bib"); a.set_defaults(fn=cmd_bib)

    args = p.parse_args()
    args.workspace = args.workspace or args.workspace_pre or "."
    args.fn(args)


if __name__ == "__main__":
    main()

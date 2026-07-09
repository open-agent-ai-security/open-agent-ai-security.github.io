#!/usr/bin/env python3
# Copyright 2026 Exabeam, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Automated GoatCounter feed for the /stats dashboard.

Pulls the per-hit CSV export via the GoatCounter API (POST /api/v0/export), then
MERGES it with the committed historical baseline (stats/goatcounter-baseline/,
frozen before automation, tokens hashed) and writes the combined tables to
stats/goatcounter-merged/ in the exact JSONL shape generate.py already reads.
generate.py picks up the merged dir automatically. No manual zip; no data loss.

Merge is by (hashed) path string: real paths like /praxen unify across the two
windows while each tokenized (mkt_tok) path stays distinct — so the campaign /
scanner split is preserved. Token-safe: mkt_tok / mc_phishing values are hashed
exactly like the baseline, so nothing per-recipient is ever written.

Auth: $GOATCOUNTER_API_TOKEN (in CI, the repo secret). The per-hit export needs
the site's "Store individual pageviews" setting on. Exports are limited to once
per hour by GoatCounter.

  python3 stats/fetch_goatcounter.py            # pull + merge + write merged dir
  python3 stats/fetch_goatcounter.py --csv F     # aggregate a local CSV (testing)
"""
import os, sys, json, time, gzip, io, csv, re, hashlib, argparse
import urllib.request, urllib.error

SITE = "https://open-agent-ai-security.goatcounter.com"
HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, "goatcounter-baseline")
OUT = os.path.join(HERE, "goatcounter-merged")

_TOKEN_RE = re.compile(r"((?:mkt_tok|mc_phishing_protection_id)=)([^&]+)")
def redact(path):
    return _TOKEN_RE.sub(lambda m: m.group(1) + "h" + hashlib.sha1(m.group(2).encode()).hexdigest()[:16], path)


# ── GoatCounter API ──────────────────────────────────────────────────────────
def pull_csv():
    tok = os.environ.get("GOATCOUNTER_API_TOKEN")
    if not tok:
        sys.exit("GOATCOUNTER_API_TOKEN not set")

    def api(method, path):
        req = urllib.request.Request(
            SITE + "/api/v0" + path, method=method,
            data=(b'{"format":"csv"}' if method == "POST" else None),
            headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()

    code, b = api("POST", "/export")
    if code != 202:
        raise RuntimeError(f"POST /export -> {code}: {b.decode('utf-8','replace')[:200]}")
    eid = json.loads(b)["id"]
    for _ in range(120):
        code, b = api("GET", f"/export/{eid}")
        if json.loads(b).get("finished_at"):
            break
        time.sleep(2)
    else:
        raise RuntimeError("export did not finish")
    code, body = api("GET", f"/export/{eid}/download")
    if code != 200:
        raise RuntimeError(f"download -> {code}")
    try:
        return gzip.decompress(body).decode("utf-8", "replace")
    except Exception:
        return body.decode("utf-8", "replace")


# ── records: path-string-keyed, so the two windows merge cleanly ─────────────
# Each source yields four maps keyed by strings (not numeric ids):
#   titles[path]                       -> title
#   hits[(path, hour, ref, scheme)]    -> count
#   sizes[(path, day, width)]          -> count
#   locs[(path, day, location)]        -> count
def _blank():
    return {"titles": {}, "hits": {}, "sizes": {}, "locs": {}}

def records_from_csv(text, cutoff_day):
    rows = list(csv.reader(io.StringIO(text)))
    rec = _blank()
    if not rows:
        return rec
    hdr = rows[0]
    idx = {h: i for i, h in enumerate(hdr)}
    def col(r, name, d=""):
        if name == "Path":                       # header cell is '<ver>Path'; data is col 0
            return r[0] if r else d
        i = idx.get(name)
        return r[i] if i is not None and i < len(r) else d
    for r in rows[1:]:
        if not r:
            continue
        if col(r, "Event", "0") not in ("0", "", "false", "False"):   # pageviews only
            continue
        if col(r, "Bot", "0") not in ("0", "", "false", "False"):     # drop GC-flagged bots
            continue
        date = col(r, "Date")
        if len(date) < 10:
            continue
        day = date[:10]
        if cutoff_day and day <= cutoff_day:      # baseline owns everything <= cutoff
            continue
        path = redact(col(r, "Path"))
        hour = date[:13] + ":00:00Z"
        ref, scheme = redact(col(r, "Referrer")), col(r, "Referrer scheme")  # redact: a referrer could carry ?mkt_tok=
        rec["titles"].setdefault(path, col(r, "Title"))
        rec["hits"][(path, hour, ref, scheme)] = rec["hits"].get((path, hour, ref, scheme), 0) + 1
        ss = col(r, "Screen size")
        if ss and "," in ss:
            try:
                w = int(ss.split(",")[0])
            except ValueError:
                w = 0
            if w:
                rec["sizes"][(path, day, w)] = rec["sizes"].get((path, day, w), 0) + 1
        loc = col(r, "Location")
        if loc:
            rec["locs"][(path, day, loc)] = rec["locs"].get((path, day, loc), 0) + 1
    return rec

def records_from_baseline():
    rec = _blank()
    def rd(f):
        p = os.path.join(BASELINE, f)
        return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.exists(p) else []
    pid2path, pid2title = {}, {}
    for r in rd("paths.jsonl"):
        pid2path[r["id"]] = r["path"]
        pid2title[r["id"]] = r.get("title", "")
        rec["titles"].setdefault(r["path"], r.get("title", ""))
    rid2ref = {r["id"]: (r.get("ref", ""), r.get("ref_scheme", "o")) for r in rd("refs.jsonl")}
    for h in rd("hit_stats.jsonl"):
        p = pid2path.get(h["path_id"])
        if p is None:
            continue
        ref, scheme = rid2ref.get(h["ref_id"], ("", "o"))
        k = (p, h["hour"], ref, scheme)
        rec["hits"][k] = rec["hits"].get(k, 0) + h["count"]
    for s in rd("size_stats.jsonl"):
        p = pid2path.get(s["path_id"])
        if p is None:
            continue
        k = (p, s["day"], s["width"])
        rec["sizes"][k] = rec["sizes"].get(k, 0) + s["count"]
    for l in rd("location_stats.jsonl"):
        p = pid2path.get(l["path_id"])
        if p is None:
            continue
        k = (p, l["day"], l["location"])
        rec["locs"][k] = rec["locs"].get(k, 0) + l["count"]
    return rec

def merge(a, b):
    m = _blank()
    for src in (a, b):
        m["titles"].update({k: v for k, v in src["titles"].items() if v or k not in m["titles"]})
        for key in ("hits", "sizes", "locs"):
            for k, v in src[key].items():
                m[key][k] = m[key].get(k, 0) + v
    return m


# ── emit the merged JSONL tables generate.py reads ───────────────────────────
def write_merged(rec, out_dir):
    if os.path.isdir(out_dir):
        import shutil
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    # assign numeric ids
    pid = {p: i + 1 for i, p in enumerate(sorted(rec["titles"]))}
    ref_keys = sorted({(k[2], k[3]) for k in rec["hits"]})
    rid = {rk: i + 1 for i, rk in enumerate(ref_keys)}

    def dump(fn, rows):
        with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")

    dump("paths.jsonl", ({"id": pid[p], "path": p, "title": rec["titles"].get(p, "")}
                         for p in sorted(rec["titles"])))
    dump("refs.jsonl", ({"id": rid[rk], "ref": rk[0], "ref_scheme": rk[1]} for rk in ref_keys))
    dump("hit_stats.jsonl", ({"hour": h, "path_id": pid[p], "ref_id": rid[(ref, sch)], "count": c}
                             for (p, h, ref, sch), c in rec["hits"].items()))
    dump("size_stats.jsonl", ({"day": d, "path_id": pid[p], "width": w, "count": c}
                              for (p, d, w), c in rec["sizes"].items()))
    dump("location_stats.jsonl", ({"day": d, "path_id": pid[p], "location": loc, "count": c}
                                  for (p, d, loc), c in rec["locs"].items()))
    days = sorted({k[1][:10] for k in rec["hits"]})
    json.dump({"export_version": "merged", "created_by": "fetch_goatcounter.py",
               "window": [days[0] if days else None, days[-1] if days else None]},
              open(os.path.join(out_dir, "info.json"), "w"), indent=2)
    return len(pid), len(rec["hits"]), (days[0] if days else "-"), (days[-1] if days else "-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="aggregate a local CSV file instead of pulling (testing)")
    args = ap.parse_args()

    cutoff = None
    bi = os.path.join(BASELINE, "info.json")
    if os.path.exists(bi):
        cutoff = (json.load(open(bi)).get("_baseline") or {}).get("cutoff_day")

    text = open(args.csv, encoding="utf-8").read() if args.csv else pull_csv()
    live = records_from_csv(text, cutoff)
    base = records_from_baseline()
    print(f"baseline: {len(base['titles'])} paths, {sum(base['hits'].values())} hits"
          f"  | live (> {cutoff}): {len(live['titles'])} paths, {sum(live['hits'].values())} hits")
    merged = merge(base, live)
    npaths, nhits, d0, d1 = write_merged(merged, OUT)
    print(f"wrote {OUT}: {npaths} paths, {len(merged['hits'])} hit rows, "
          f"{sum(merged['hits'].values())} total hits, window {d0} -> {d1}")


if __name__ == "__main__":
    main()

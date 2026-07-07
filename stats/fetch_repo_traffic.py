#!/usr/bin/env python3
# Copyright 2026 Exabeam, Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Snapshot GitHub repo traffic (Insights → Traffic) for the community projects.

GitHub's traffic API keeps only a 14-day ROLLING window and purges anything
older, so the only way to build real history is to snapshot regularly and
accumulate. This script writes the current snapshot to stats/repo-traffic.json;
generate.py reads THAT file (never the live API) so report generation stays
offline, deterministic, and runnable by anyone without repo push access.

  views / clones : {count, uniques} over the trailing 14 days (+ daily buckets)
  referrers      : top ~10 referring sites (14d totals)
  paths          : top ~10 repo paths (14d totals)

Auth: needs push access to each repo (GitHub gates traffic behind it). Uses the
`gh` CLI, which works locally (your gh login) and in GitHub Actions. To read
MULTIPLE repos from one job you need a token with Administration:read on each —
the default Actions GITHUB_TOKEN only sees its own repo. See the (future)
.github/workflows/repo-traffic.yml.

Run:  python3 stats/fetch_repo_traffic.py
"""
import json, subprocess, datetime, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRIPT_DIR, "repo-traffic.json")

# project-key → GitHub repo. Keep in sync with REPO in generate.py.
REPOS = {
    "praxen":   "open-agent-ai-security/praxen",
    "observra": "open-agent-ai-security/observra",
}


def gh(path):
    """Call the GitHub REST API through the gh CLI; return parsed JSON."""
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"gh api {path} failed:\n{out.stderr.strip()}")
    return json.loads(out.stdout)


def snapshot(repo):
    v = gh(f"/repos/{repo}/traffic/views")
    c = gh(f"/repos/{repo}/traffic/clones")
    refs = gh(f"/repos/{repo}/traffic/popular/referrers")
    paths = gh(f"/repos/{repo}/traffic/popular/paths")
    return {
        "repo": repo,
        "views":  {"count": v.get("count", 0), "uniques": v.get("uniques", 0),
                   "days": v.get("views", [])},
        "clones": {"count": c.get("count", 0), "uniques": c.get("uniques", 0),
                   "days": c.get("clones", [])},
        "referrers": [{"referrer": r["referrer"], "count": r["count"],
                       "uniques": r["uniques"]} for r in refs],
        "paths": [{"path": p["path"], "count": p["count"],
                   "uniques": p["uniques"]} for p in paths],
    }


def _merge_days(old, new):
    """Union of daily buckets by timestamp; the newer pull wins for a given day
    (a still-open day gets more complete on later pulls). This is how we ACCUMULATE
    history past GitHub's 14-day purge — old days survive, new days append."""
    by_ts = {d["timestamp"]: d for d in old}
    for d in new:
        by_ts[d["timestamp"]] = d
    return sorted(by_ts.values(), key=lambda d: d["timestamp"])


def main():
    # Load any prior snapshot so daily history accumulates instead of being lost.
    existing = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as fh:
            existing = json.load(fh).get("repos", {})

    repos = {}
    for key, repo in REPOS.items():
        snap = snapshot(repo)
        if key in existing:                       # keep + extend the daily history
            for metric in ("views", "clones"):
                snap[metric]["days"] = _merge_days(
                    existing[key].get(metric, {}).get("days", []), snap[metric]["days"])
        repos[key] = snap

    data = {
        "snapshot_utc": datetime.datetime.utcnow().date().isoformat(),
        "window_days": 14,          # top-level count/uniques = trailing-14d totals
        "repos": repos,             # views/clones .days = accumulated full history
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print(f"Wrote {OUT}  (snapshot {data['snapshot_utc']})")
    for key, r in data["repos"].items():
        print(f"  {key:<10} views {r['views']['count']:>5} "
              f"({r['views']['uniques']} uniq, {len(r['views']['days'])}d hist) · "
              f"clones {r['clones']['count']:>5} ({r['clones']['uniques']} uniq)")


if __name__ == "__main__":
    main()

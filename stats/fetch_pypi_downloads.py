#!/usr/bin/env python3
# Copyright 2026 Exabeam, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Snapshot PyPI download counts for the community's published packages.

pypistats.org keeps only a ~180-day window, so — exactly like
fetch_repo_traffic.py does for GitHub traffic — we snapshot regularly and
ACCUMULATE the daily buckets into stats/pypi-downloads.json. generate.py reads
THAT file (never the live API), so report generation stays offline and
deterministic, and it derives the last-day/7/30/total windows from the
accumulated history (one source of truth = the daily series).

Counts are ALL-INCLUSIVE (mirrors=true): every install pip records, including
CI and mirror pulls. Read them as a trend, not a headcount.

Availability: pypistats is a free community service and occasionally 429s or
5xxs. This script FAILS SOFT — on any error for a package it keeps that
package's prior data unchanged and moves on; the next successful run merges the
missing days back in, so history self-heals rather than getting a gap or a crash.

No auth needed. Only observra is on PyPI; Praxen ships as a Claude Code / Codex
plugin, so it has no PyPI footprint to count.

Run:  python3 stats/fetch_pypi_downloads.py
"""
import json, os, datetime, urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRIPT_DIR, "pypi-downloads.json")

# project-key → PyPI package name. Keep in sync with PYPI in generate.py.
PACKAGES = {"observra": "observra"}
API = "https://pypistats.org/api/packages/{pkg}/overall?mirrors=true"
RELEASES_API = "https://pypi.org/pypi/{pkg}/json"
_UA = {"User-Agent": "oaas-stats-bot (+https://open-agent-ai-security.github.io)"}


def _fetch_days(pkg):
    """All-inclusive daily download series for a package, as [{date, downloads}]."""
    req = urllib.request.Request(API.format(pkg=pkg), headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r).get("data", [])
    return [{"date": d["date"], "downloads": d["downloads"]} for d in data]


def _fetch_releases(pkg):
    """Release upload dates from PyPI, as [{version, date}] — annotate the trend so
    download spikes can be read against ships. Cached into the JSON so generate.py
    never touches the network."""
    req = urllib.request.Request(RELEASES_API.format(pkg=pkg), headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        rel = json.load(r).get("releases", {})
    out = [{"version": v, "date": files[0]["upload_time"][:10]}
           for v, files in rel.items() if files]
    return sorted(out, key=lambda x: x["date"])


def _merge_days(old, new):
    """Union of daily buckets by date; the newer pull wins for a given date (a
    still-open day gets more complete later). This ACCUMULATES history past the
    pypistats retention window — old days survive, new days append."""
    by_date = {d["date"]: d for d in old}
    for d in new:
        by_date[d["date"]] = d
    return sorted(by_date.values(), key=lambda d: d["date"])


def main():
    existing = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as fh:
            existing = json.load(fh).get("packages", {})

    packages = {}
    for key, pkg in PACKAGES.items():
        prior = existing.get(key)
        entry = dict(prior) if prior else {"package": pkg}  # start from prior; each
        #                                    fetch below overwrites only on success
        try:                                            # daily downloads — fail soft
            entry["days"] = _merge_days(prior.get("days", []) if prior else [],
                                        _fetch_days(pkg))
        except Exception as e:
            print(f"::warning::pypistats fetch for {pkg} failed ({e}); keeping prior days")
        try:                                            # release dates — fail soft
            entry["releases"] = _fetch_releases(pkg)
        except Exception as e:
            print(f"::warning::PyPI release fetch for {pkg} failed ({e}); keeping prior releases")
        if entry.get("days"):                           # only surface a package with data
            packages[key] = entry
            print(f"  {key:<10} {sum(d['downloads'] for d in entry['days']):>7} total "
                  f"({len(entry['days'])}d history, {len(entry.get('releases', []))} releases)")

    data = {"snapshot_utc": datetime.datetime.utcnow().date().isoformat(),
            "packages": packages}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print(f"Wrote {OUT}  (snapshot {data['snapshot_utc']})")


if __name__ == "__main__":
    main()

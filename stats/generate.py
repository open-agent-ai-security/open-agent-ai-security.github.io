#!/usr/bin/env python3
# Copyright 2026 Exabeam, Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Community traffic report generator — Open Agent and AI Security Community.

Standing, overall traffic tracking across all community Pages sites. Rolls the
whole community up into one view, then breaks traffic out per project (Praxen,
Observra, … add more as they launch).

This is deliberately NOT Praxen's launch retrospective (stats/ in the praxen
repo). That one is a one-time, launch-focused post-mortem. This is the ongoing
"how is traffic doing across everything" dashboard.

Emits one self-contained HTML report (no external deps — open in a browser or
attach to an email as-is):
  - index.html   (served at https://open-agent-ai-security.github.io/stats/)

Data source (identical to Praxen — one shared account):
  - GoatCounter export : the unzipped `open-agent-ai-security` community-account
    export (NOT committed — per-account analytics, keep local). Every org Pages
    site reports to this single account, so one export contains every path: the
    community root `/`, `/praxen/*`, `/observra/*`, …

Adding a project: append one line to PROJECTS below. Anything that matches no
project prefix rolls up into "Community" (the root landing + shared pages).

Regenerate:
  1. GoatCounter → Settings → Export → download, then unzip into stats/
     (goatcounter-export*/).
  2. python3 stats/generate.py
     With no export present it renders from built-in SAMPLE data, clearly
     marked, so the layout can be previewed before real data exists.
"""
import json, collections, datetime, glob, os, urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRIPT_DIR, "index.html")

# ── Project registry ─────────────────────────────────────────────────────────
# (key, label, path_prefix, color). Order = display order under Community.
# Add a project by appending one row; its color themes its bar/section.
PROJECTS = [
    ("praxen",   "Praxen",   "/praxen",   "#ff7a2e"),
    ("observra", "Observra", "/observra", "#37c2f0"),
]
COMMUNITY = ("community", "Community", "", "#5b8def")  # everything not under a project

# Public repo per project, for the GitHub-stars section (star count fetched live
# at build time; the trend chart is committed as community-stars.svg). A project
# with no entry here simply doesn't appear in the stars section.
REPO = {
    "praxen":   "open-agent-ai-security/praxen",
    "observra": "open-agent-ai-security/observra",
}
STARS_SVG = os.path.join(SCRIPT_DIR, "community-stars.svg")  # combined star-history chart


def bucket_of(path):
    """Map a GoatCounter path to a project key, or 'community' if it matches none."""
    p = (path or "/").rstrip("/") or "/"
    for key, _label, prefix, _color in PROJECTS:
        pre = prefix.rstrip("/")
        if pre and (p == pre or p.startswith(pre + "/")):
            return key
    return COMMUNITY[0]


BUCKETS = [COMMUNITY] + PROJECTS                      # display order
LABEL = {k: l for k, l, _p, _c in BUCKETS}
COLOR = {k: c for k, _l, _p, c in BUCKETS}


# ── Load data (real export, else built-in sample) ────────────────────────────
def find_export():
    # Only accept a directory that actually holds an export (has paths.jsonl),
    # so stray/empty goatcounter-* dirs don't get picked up.
    cands = (glob.glob(os.path.join(SCRIPT_DIR, "goatcounter-export*", ""))
             + glob.glob("/tmp/gc*/goatcounter-*/"))
    for c in cands:
        if os.path.exists(os.path.join(c, "paths.jsonl")):
            return c
    return None


def sample_data():
    """Small synthetic dataset shaped like a GoatCounter export, so the report
    can be previewed without real analytics. Observra ramps (recent launch)."""
    paths = {1: "/", 2: "/praxen", 3: "/praxen/guide/getting-started/adk",
             4: "/observra", 5: "/observra/guide/api/observra.html",
             6: "/observra/guide/getting-started/adk"}
    refs = {1: "(direct)", 2: "linkedin.com", 3: "github.com", 4: "google",
            5: "open-agent-ai-security.github.io"}
    days = [f"2026-06-{d:02d}" for d in range(22, 31)] + ["2026-07-01"]
    hits = []
    for i, day in enumerate(days):
        h = day + "T12:00:00Z"
        hits += [
            {"hour": h, "path_id": 1, "ref_id": 1, "count": 18 + i * 2},
            {"hour": h, "path_id": 1, "ref_id": 2, "count": 6 + i},
            {"hour": h, "path_id": 1, "ref_id": 4, "count": 3 + i // 2},
            {"hour": h, "path_id": 2, "ref_id": 1, "count": 10},
            {"hour": h, "path_id": 2, "ref_id": 3, "count": 4},
            {"hour": h, "path_id": 3, "ref_id": 5, "count": 3},
            {"hour": h, "path_id": 4, "ref_id": 2, "count": 4 + i * 3},
            {"hour": h, "path_id": 5, "ref_id": 5, "count": 2 + i},
            {"hour": h, "path_id": 6, "ref_id": 3, "count": 1 + i},
        ]
    locs = [{"location": l, "count": c} for l, c in
            [("US-CA", 120), ("US-NY", 70), ("GB", 55), ("US-TX", 40), ("DE", 33),
             ("IN", 28), ("CA", 22), ("FR", 18), ("AU", 15), ("NL", 12)]]
    return paths, refs, hits, locs


EXPORT_DIR = find_export()
IS_SAMPLE = EXPORT_DIR is None

if IS_SAMPLE:
    paths, refs, hits, locs = sample_data()
else:
    def load(f):
        with open(os.path.join(EXPORT_DIR, f), encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]
    paths = {p["id"]: p["path"] for p in load("paths.jsonl")}
    refs = {r["id"]: (r["ref"] or "(direct)") for r in load("refs.jsonl")}
    hits = load("hit_stats.jsonl")
    locs = load("location_stats.jsonl")


# ── Aggregate ────────────────────────────────────────────────────────────────
def catf(ref):
    r = (ref or "").lower()
    if r in ("", "(direct)"):
        return "Direct"
    if "linkedin" in r or "lnkd" in r:
        return "LinkedIn"
    if "github.io" in r:
        return "Internal site nav"
    if "github.com" in r:
        return "GitHub.com"
    if any(s in r for s in ("google", "bing", "duckduckgo")):
        return "Search"
    if "teams" in r or "office.net" in r or "microsoft" in r:
        return "MS Teams"
    if "slack" in r:
        return "Slack"
    if "t.co" in r or "twitter" in r or "x.com" in r:
        return "X/Twitter"
    if "exabeam" in r:
        return "Exabeam.com"
    return "Other / press"


total = sum(h["count"] for h in hits)
days = sorted({h["hour"][:10] for h in hits})
bucket_total = collections.Counter()
byday = collections.Counter()
byday_bucket = collections.defaultdict(collections.Counter)
refcat = collections.Counter()
bypath = collections.Counter()

for h in hits:
    d = h["hour"][:10]
    path = paths.get(h["path_id"], "")
    b = bucket_of(path)
    bucket_total[b] += h["count"]
    byday[d] += h["count"]
    byday_bucket[b][d] += h["count"]
    refcat[catf(refs.get(h["ref_id"], ""))] += h["count"]
    bypath[h["path_id"]] += h["count"]

toppages = sorted(((paths.get(pid, ""), c) for pid, c in bypath.items()),
                  key=lambda x: -x[1])[:12]
byloc = collections.Counter()
for l in locs:
    byloc[l["location"]] += l["count"]
toploc = byloc.most_common(10)
top_bucket = max((k for k, _l, _p, _c in PROJECTS), key=lambda k: bucket_total[k],
                 default=None)
today = datetime.date.today().isoformat()


def fetch_stars(repo):
    """Live stargazer count via the public GitHub API; None if offline/unavailable."""
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "oaas-stats"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.load(r).get("stargazers_count")
    except Exception:
        return None


stars = {k: fetch_stars(REPO[k]) for k, _l, _p, _c in PROJECTS if k in REPO}
stars_svg = ""
if os.path.exists(STARS_SVG):
    with open(STARS_SVG, encoding="utf-8") as _svg:
        stars_svg = _svg.read().replace(
            'width="800" height="533.333" style="stroke-width:3;font-family:xkcd;background:#fff"',
            'viewBox="0 0 800 533.333" width="100%" style="stroke-width:3;font-family:xkcd;'
            'background:#fff;max-width:760px;height:auto;display:block;margin:0 auto;border-radius:10px"')


# ── Render ───────────────────────────────────────────────────────────────────
CSS = """:root{--bg:#0a1020;--panel:rgba(255,255,255,.04);--bd:rgba(255,255,255,.09);--tx:#e9eff8;--mut:#9aabc0;--mut2:#6f819a;--ac:#5b8def;--ac2:#7aa5f2}
*{box-sizing:border-box}html,body{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.6 Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:920px;margin:0 auto;padding:38px 22px 70px}
h1{font-size:30px;margin:0 0 6px;font-weight:700;letter-spacing:-.02em}
h2{font-size:19px;margin:34px 0 14px;font-weight:700;letter-spacing:-.01em}
.sub{color:var(--mut);margin:0 0 22px;font-size:14.5px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0 6px}
.card{background:var(--panel);border:1px solid var(--bd);border-radius:14px;padding:16px}
.card b{display:block;font-size:27px;font-weight:700;color:var(--ac2);line-height:1.05}
.card span{font-size:12.5px;color:var(--mut)}
.sec{background:var(--panel);border:1px solid var(--bd);border-radius:16px;padding:20px 22px;margin-bottom:8px}
.row{display:flex;align-items:center;gap:12px;margin:7px 0;font-size:13.5px}
.rl{flex:0 0 210px;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rbar{flex:1 1 auto;background:rgba(255,255,255,.05);border-radius:6px;height:14px;overflow:hidden}
.rbar i{display:block;height:100%;border-radius:6px}
.rv{flex:0 0 130px;text-align:right;color:var(--tx);font-weight:600;font-size:12.5px}
.chip{display:inline-block;font-size:11px;padding:1px 7px;border-radius:20px;font-weight:600;vertical-align:middle}
table{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:6px}
td{padding:7px 8px;border-bottom:1px solid var(--bd);color:var(--mut)}
td.n{text-align:right;color:var(--tx);font-weight:600;width:70px}
.foot{color:var(--mut2);font-size:12px;margin-top:30px;border-top:1px solid var(--bd);padding-top:16px}
.tag{display:inline-block;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ac2);font-weight:700}
.warn{border:1px solid #7a5a1d;background:linear-gradient(160deg,rgba(255,193,64,.10),rgba(255,255,255,.01));border-radius:12px;padding:12px 16px;margin:14px 0;color:#ffd98a;font-size:13.5px}
@media(max-width:680px){.cards{grid-template-columns:repeat(2,1fr)}.rl{flex-basis:120px}}"""


def bar(label, val, vmax, sub="", color="#5b8def"):
    w = max(2, round(val / vmax * 100)) if vmax else 2
    return (f'<div class="row"><span class="rl">{label}</span>'
            f'<span class="rbar"><i style="width:{w}%;background:{color}"></i></span>'
            f'<span class="rv">{val}{(" · " + sub) if sub else ""}</span></div>')


def pct(v):
    return f"{round(v / total * 100)}%" if total else "0%"


P = []
P.append(f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
         f'<meta name="viewport" content="width=device-width, initial-scale=1">'
         f'<title>Community Traffic — Overview</title><style>{CSS}</style></head>'
         f'<body><div class="wrap">')
P.append('<span class="tag">GoatCounter · open-agent-ai-security</span>'
         '<h1>Community Traffic — Overview</h1>')
P.append(f'<p class="sub">All community Pages sites, with per-project breakout. '
         f'Window <b>{days[0]} → {days[-1]}</b> (UTC · latest day may be partial). '
         f'One shared GoatCounter account; GoatCounter undercounts (blockers, no-JS), '
         f'so true traffic is higher.</p>')

if IS_SAMPLE:
    P.append('<div class="warn"><b>SAMPLE DATA</b> — no GoatCounter export found, so '
             'this is built-in placeholder data to preview the layout. Drop a real '
             'export into <code>stats/</code> and re-run to replace it.</div>')

# headline cards
P.append('<div class="cards">')
P.append(f'<div class="card"><b>{total:,}</b><span>Total pageviews</span></div>')
P.append(f'<div class="card"><b>{len(PROJECTS)}</b><span>Projects tracked</span></div>')
P.append(f'<div class="card"><b>{len(days)}</b><span>Days in window</span></div>')
P.append(f'<div class="card"><b>{LABEL.get(top_bucket, "—")}</b>'
         f'<span>Top project</span></div>')
P.append('</div>')

# traffic by bucket
P.append('<h2>Traffic by project</h2><div class="sec">')
vmax = max(bucket_total.values()) if bucket_total else 0
for key, label, _prefix, color in BUCKETS:
    c = bucket_total.get(key, 0)
    P.append(bar(f'{label}', c, vmax, sub=pct(c), color=color))
P.append('</div>')

# daily pageviews (overall)
P.append('<h2>Daily pageviews (all community)</h2><div class="sec">')
dmax = max(byday.values()) if byday else 0
for d in days:
    P.append(bar(d, byday[d], dmax, color="#5b8def"))
P.append('</div>')

# top referrers
P.append('<h2>Top referrers</h2><div class="sec">')
rmax = max(refcat.values()) if refcat else 0
for name, c in refcat.most_common(10):
    P.append(bar(name, c, rmax, sub=pct(c), color="#7aa5f2"))
P.append('</div>')

# top pages (labelled by project)
P.append('<h2>Top pages</h2><div class="sec"><table>')
for path, c in toppages:
    b = bucket_of(path)
    chip = (f'<span class="chip" style="background:{COLOR[b]}22;color:{COLOR[b]}">'
            f'{LABEL[b]}</span>')
    P.append(f'<tr><td>{chip} <code>{path or "/"}</code></td><td class="n">{c}</td></tr>')
P.append('</table></div>')

# geography
P.append('<h2>Top locations</h2><div class="sec">')
lmax = toploc[0][1] if toploc else 0
for loc, c in toploc:
    P.append(bar(loc, c, lmax, color="#4db6ac"))
P.append('</div>')

# GitHub stars (counts fetched live; combined trend chart from star-history.com)
P.append('<h2>GitHub stars</h2>')
P.append('<p class="sub">Live stargazer counts per project (GitHub API), with the '
         'combined star-history trend below.</p>')
P.append('<div class="cards" style="grid-template-columns:repeat(2,1fr)">')
for key, label, _prefix, color in PROJECTS:
    if key in REPO:
        n = stars.get(key)
        val = f'&#9733; {n:,}' if n is not None else '&mdash;'
        P.append(f'<div class="card"><b style="color:{color}">{val}</b>'
                 f'<span>{label} &middot; <code>{REPO[key]}</code></span></div>')
P.append('</div>')
if stars_svg:
    P.append(f'<div class="sec" style="background:#fff;padding:14px 14px 6px;overflow:hidden">{stars_svg}</div>')
    P.append(f'<p class="sub" style="margin:10px 0 0">Chart: star-history.com &middot; snapshot {today}. '
             'A launch is a spike; the slope over the following weeks is the real adoption signal.</p>')

P.append(f'<p class="foot">Generated {today} by <code>stats/generate.py</code>. '
         f'Sources: GoatCounter export (open-agent-ai-security community account)'
         f'{" — SAMPLE placeholder data" if IS_SAMPLE else ""} &middot; stars via GitHub API '
         f'&middot; star-history.com. GitHub repo <i>traffic</i> (clones, views) is a '
         f'separate property and not included here.</p>')
P.append('</div></body></html>')

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("".join(P))

kind = "SAMPLE" if IS_SAMPLE else "real export"
print(f"Wrote {OUT}")
print(f"  {kind}: {total:,} pageviews · {len(days)} days ({days[0]}→{days[-1]})")
for key, label, _prefix, _color in BUCKETS:
    print(f"  {label:<12} {bucket_total.get(key, 0):>7,}  {pct(bucket_total.get(key, 0))}")
print("  stars: " + ", ".join(f"{LABEL[k]} {v if v is not None else '—'}" for k, v in stars.items()))

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

Data sources:
  - GoatCounter export .... Pages-site (hero website) traffic (goatcounter-export*/)
  - repo-traffic.json ..... GitHub repo views/clones, written by fetch_repo_traffic.py

"Reach" combines the two: real site views (the full GoatCounter export window) +
GitHub repo views — ACCUMULATED daily (fetch_repo_traffic.py snapshots GitHub's
trailing-14-day window each day and merges the buckets, so the history survives
GitHub's purge). Reach sums the whole accumulated series, NOT the 14-day count,
so total reach is cumulative and never drops as launch days age out. We keep the
full site window too rather than truncating to GitHub's — no reason to drop real
data we have. Repo CLONES are never in reach (they're CI/mirror-bot heavy). Missing
repo-traffic.json → repo figures just omit.

Regenerate:
  1. GoatCounter → Settings → Export → download, unzip into stats/ (goatcounter-export*/).
  2. python3 stats/fetch_repo_traffic.py   (needs gh auth w/ push access; writes
     repo-traffic.json — skip if you only want site figures)
  3. python3 stats/generate.py
     With no export present it renders from built-in SAMPLE data, clearly
     marked, so the layout can be previewed before real data exists.

═══════════════════════════════════════════════════════════════════════════════
EMAIL-CAMPAIGN / BOT FILTERING  (read this before trusting any number)
═══════════════════════════════════════════════════════════════════════════════
When Marketing sends a Marketo email blast that links here, the numbers spike by
~6× for a day — but almost none of it is human. Corporate email security
(Microsoft Safe Links, Mimecast, Proofpoint, EdgePilot, …) auto-fetches every
link in every delivered message, often 2× per link (gateway + browser
isolation). Those fetches DO run JS, so GoatCounter counts them as pageviews.

Diagnosed on the 2026-07-01 blast: 10,912 views in one day (78% of a 20-day
window), 91% locked to a single 1920px viewport, ~0% mobile, 4,500+ "distinct
paths" that were really ONE page × thousands of unique Marketo tokens.

We DON'T want to blind-drop that day (real humans clicked too), so we classify
every pageview into three classes and report them separately:

  1. ORGANIC ............ real traffic. The default. Never filtered.
  2. CAMPAIGN-AUTOMATED . email-security scanners triggered by a blast.
  3. CAMPAIGN-HUMAN ..... a real person who clicked the email (~1% — normal CTR).

How each pageview is classified (see classify_traffic() below):

  • CAMPAIGN is identified by the Marketo token in the URL: a path containing
    `mkt_tok=` (or `mc_phishing_protection_id=`, Mimecast's tag). Every unique
    token = one recipient/scan, so the token IS the per-visitor key (= path_id).

  • Within the campaign cohort, a token is promoted to HUMAN only on an
    affirmative human signal — scanners can't easily fake either:
      – MOBILE viewport (<600px width) — scanners run headless desktop; OR
      – a TIME-SEPARATED revisit — the same token hit in ≥2 distinct hours
        (a scanner fires once on delivery; a human comes back later, even days).
    Raw repeat-count does NOT qualify: 80% of tokens get exactly 2 hits in the
    SAME hour — that's the redirect-fetch + direct-fetch double-scan, not a human.

  • TOKEN-STRIPPED scanners: some scanners pre-resolve the link and hit the bare
    URL (no token). They betray themselves by clustering in the blast's BURST
    hours (a (day,hour) bucket carrying ≥ BURST_MIN tokenized hits) with a
    lost/forwarded referrer (direct or email.exabeam.com). A real human who
    clicks KEEPS the token (they ride the email→redirect→token URL), so bare +
    referrer-less + in-burst-hour = scanner. Bare hits with a genuine referrer
    (LinkedIn, internal nav) stay ORGANIC.

Everything downstream (project split, daily trend, referrers, top pages, geo)
uses REAL = ORGANIC + CAMPAIGN-HUMAN. The automated volume is shown once, in its
own "Traffic quality" section, and in a footnote — never hidden, never headline.

Tuning knobs live in the CLASSIFY block below (BURST_MIN, MOBILE_MAX_W). If a
future export's fingerprint differs, re-diagnose before trusting the split.
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

# project-key → PyPI package, for the downloads section. No entry ⇒ not shown.
# observra only; Praxen ships as a plugin, not a pip package. Download windows are
# derived from the accumulated daily series in pypi-downloads.json (all-inclusive).
PYPI = {"observra": "observra"}


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
    # Prefer the automated merged feed (fetch_goatcounter.py: baseline + live
    # per-hit API export). Fall back to a manually-unzipped export dir. Only
    # accept a dir that actually holds an export (has paths.jsonl), so stray/
    # empty goatcounter-* dirs don't get picked up.
    cands = ([os.path.join(SCRIPT_DIR, "goatcounter-merged", "")]
             + glob.glob(os.path.join(SCRIPT_DIR, "goatcounter-export*", ""))
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
    sizes = []                              # sample has no per-page screen sizes
else:
    def load(f):
        with open(os.path.join(EXPORT_DIR, f), encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]
    paths = {p["id"]: p["path"] for p in load("paths.jsonl")}
    refs = {r["id"]: (r["ref"] or "(direct)") for r in load("refs.jsonl")}
    hits = load("hit_stats.jsonl")
    locs = load("location_stats.jsonl")
    sizes = load("size_stats.jsonl")        # {day, path_id, width, count} — for bot screen

# GitHub repo traffic snapshot (written by fetch_repo_traffic.py; 14-day rolling
# window — all GitHub retains). Read from disk, never the live API, so generation
# stays offline/deterministic. Missing file → repo columns simply don't render.
REPO_TRAFFIC = os.path.join(SCRIPT_DIR, "repo-traffic.json")
repo_traffic = {}
if os.path.exists(REPO_TRAFFIC):
    with open(REPO_TRAFFIC, encoding="utf-8") as _fh:
        _rt = json.load(_fh)
    repo_traffic = _rt.get("repos", {})

# PyPI downloads (accumulated daily series; windows derived below). observra only.
PYPI_DL = os.path.join(SCRIPT_DIR, "pypi-downloads.json")
pypi_dl = {}
if os.path.exists(PYPI_DL):
    with open(PYPI_DL, encoding="utf-8") as _fh:
        _pd = json.load(_fh)
    pypi_dl = _pd.get("packages", {})

# Key dates (launches, events) annotated on the Daily Views chart. Edit
# key-dates.json: {"YYYY-MM-DD": "label"}; keys starting with "_" are ignored.
KEY_DATES = os.path.join(SCRIPT_DIR, "key-dates.json")
key_dates = {}
if os.path.exists(KEY_DATES):
    with open(KEY_DATES, encoding="utf-8") as _fh:
        key_dates = {k: v for k, v in json.load(_fh).items() if not k.startswith("_")}

# (Featured social posts moved to the LinkedIn stats page; see make_linkedin.py.)


# ── Classify: real vs. email-campaign scanner traffic ────────────────────────
# See the "EMAIL-CAMPAIGN / BOT FILTERING" note in the module docstring for the
# full rationale. This block labels every pageview ORGANIC / CAMPAIGN-HUMAN /
# CAMPAIGN-AUTOMATED so the rest of the report can show real traffic only.

BURST_MIN = 50      # tokenized hits in one (day,hour) → that hour is a blast burst
MOBILE_MAX_W = 600  # screen width (px) below which we call a hit "mobile" (human)


def is_campaign_path(pid):
    """A URL carrying a Marketo (or Mimecast) tracking token = campaign cohort."""
    p = (paths.get(pid, "") or "").lower()
    return ("mkt_tok=" in p) or ("mc_phishing_protection_id=" in p)


def _ref_lost(rid):
    """Referrer a token-stripping scanner leaves behind: none, or the email host."""
    r = (refs.get(rid, "") or "").lower()
    return r in ("", "(direct)") or "exabeam" in r


# Per-token (= per-path_id) human signals, gathered once.
_tok_hours = collections.defaultdict(set)   # distinct hours a token was hit in
_tok_send = {}                               # earliest date a token was seen (its send)
for _h in hits:
    if is_campaign_path(_h["path_id"]):
        _tok_hours[_h["path_id"]].add(_h["hour"])
        _d, _p = _h["hour"][:10], _h["path_id"]
        if _p not in _tok_send or _d < _tok_send[_p]:
            _tok_send[_p] = _d
_tok_mobile = set()                          # tokens ever loaded at a mobile width
for _s in sizes:
    if 0 < _s.get("width", 0) < MOBILE_MAX_W and is_campaign_path(_s["path_id"]):
        _tok_mobile.add(_s["path_id"])

# Blast burst hours: (day,hour) buckets carrying heavy tokenized volume. Defined
# by volume (not mere presence) so a lone token revisit days later isn't a burst.
_tok_by_hour = collections.Counter()
for _h in hits:
    if is_campaign_path(_h["path_id"]):
        _tok_by_hour[_h["hour"]] += _h["count"]
BURST_HOURS = {hr for hr, c in _tok_by_hour.items() if c >= BURST_MIN}


def token_is_human(pid):
    """Affirmative human signal on a campaign token: mobile viewport OR a
    time-separated revisit (same token seen in ≥2 distinct hours)."""
    return (pid in _tok_mobile) or (len(_tok_hours[pid]) >= 2)


def classify(h):
    """ORGANIC | campaign_human | campaign_bot for one hit_stats row."""
    if is_campaign_path(h["path_id"]):
        return "campaign_human" if token_is_human(h["path_id"]) else "campaign_bot"
    # Bare (untokenized) hit inside a blast burst hour with a lost referrer =
    # a token-stripping scanner. Anything else untokenized is real.
    if h["hour"] in BURST_HOURS and _ref_lost(h["ref_id"]):
        return "campaign_bot"
    return "organic"


# Each detected send = one burst day. Fold all campaign traffic (blast-hour hits,
# their later revisits, and surrounding scanner trickle) into the nearest burst
# day, so every campaign hit attributes to exactly one send and the per-campaign
# rows reconcile with the totals.
_BDAYS = sorted({hr[:10] for hr in BURST_HOURS})


def _nearest_burst(dstr):
    if not _BDAYS:
        return dstr
    dd = datetime.date.fromisoformat(dstr)
    return min(_BDAYS, key=lambda b: abs((dd - datetime.date.fromisoformat(b)).days))


CLASS = {"organic": 0, "campaign_human": 0, "campaign_bot": 0}
CAMP_BY_DAY = collections.defaultdict(lambda: {"human": 0, "bot": 0})
for h in hits:
    c = classify(h)
    CLASS[c] += h["count"]
    if c in ("campaign_human", "campaign_bot"):
        base = _tok_send.get(h["path_id"], h["hour"][:10])  # token send / bare hit day
        CAMP_BY_DAY[_nearest_burst(base)][c.split("_")[1]] += h["count"]
# Campaign-bot path_ids (tokenized + never human) — used to keep scanner tokens
# out of geography, which has no hour to apply the burst rule to.
BOT_PIDS = {pid for pid in paths
            if is_campaign_path(pid) and not token_is_human(pid)}

# Detected campaigns, one per burst day (auto-flagged, accumulates as sends land).
CAMPAIGN_DAYS = sorted(CAMP_BY_DAY)


# ── Aggregate (REAL traffic only: organic + campaign-human) ──────────────────
def catf(ref):
    r = (ref or "").lower()
    if r in ("", "(direct)"):
        return "Direct (no referrer link)"
    if "linkedin" in r or "lnkd" in r:
        return "LinkedIn"
    if "github.io" in r:
        return "Internal site nav"
    if "github.com" in r:
        return "GitHub.com"
    # Search engines. "search.yahoo" (not bare "yahoo") so the Yahoo Finance
    # press syndication at finance.yahoo.com stays out of Search.
    if any(s in r for s in ("google", "bing", "duckduckgo", "brave", "ecosia",
                            "yandex", "baidu", "qwant", "kagi", "startpage",
                            "search.yahoo")):
        return "Search"
    if "teams" in r or "office.net" in r or "microsoft" in r:
        return "MS Teams"
    if "slack" in r:
        return "Slack"
    if "t.co" in r or "twitter" in r or "x.com" in r:
        return "X/Twitter"
    if "facebook" in r or "fb.me" in r:
        return "Facebook"
    if "exabeam" in r:
        return "Exabeam.com"
    return "Other / press"


# GoatCounter location codes are ISO 3166: country codes ("GB"), or US states as
# "US-CA". Map both to readable names; unknown codes fall through unchanged.
_US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "Washington DC", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "PR": "Puerto Rico",
}
_COUNTRIES = {
    "US": "United States", "GB": "United Kingdom", "CA": "Canada", "DE": "Germany",
    "FR": "France", "NL": "Netherlands", "IE": "Ireland", "ES": "Spain",
    "IT": "Italy", "PT": "Portugal", "BE": "Belgium", "CH": "Switzerland",
    "AT": "Austria", "SE": "Sweden", "NO": "Norway", "DK": "Denmark",
    "FI": "Finland", "PL": "Poland", "CZ": "Czechia", "RO": "Romania",
    "HU": "Hungary", "GR": "Greece", "UA": "Ukraine", "RU": "Russia",
    "TR": "Turkey", "IL": "Israel", "AE": "UAE", "SA": "Saudi Arabia",
    "IN": "India", "PK": "Pakistan", "BD": "Bangladesh", "SG": "Singapore",
    "MY": "Malaysia", "ID": "Indonesia", "TH": "Thailand", "VN": "Vietnam",
    "PH": "Philippines", "JP": "Japan", "KR": "South Korea", "CN": "China",
    "HK": "Hong Kong", "TW": "Taiwan", "AU": "Australia", "NZ": "New Zealand",
    "BR": "Brazil", "MX": "Mexico", "AR": "Argentina", "CL": "Chile",
    "CO": "Colombia", "PE": "Peru", "ZA": "South Africa", "NG": "Nigeria",
    "KE": "Kenya", "EG": "Egypt", "MA": "Morocco", "GH": "Ghana",
}


def loc_name(code):
    """ISO location code -> readable name. 'US-CA'->'California, US'; 'GB'->'United Kingdom'."""
    if not code:
        return "Unknown"
    if "-" in code:
        cc, sub = code.split("-", 1)
        if cc == "US" and sub in _US_STATES:
            return f"{_US_STATES[sub]}, US"
        return f"{sub}, {_COUNTRIES.get(cc, cc)}"
    return _COUNTRIES.get(code, code)


days = sorted({h["hour"][:10] for h in hits})          # full site export window

bucket_total = collections.Counter()                   # PAGES real views / project
byday = collections.Counter()
byday_search = collections.Counter()                   # real views referred by a search engine
refcat = collections.Counter()
bypath = collections.Counter()
pages_real = 0                                          # real Pages views (full window)

for h in hits:
    if classify(h) == "campaign_bot":                  # excluded from every breakdown
        continue
    pages_real += h["count"]
    d = h["hour"][:10]
    path = paths.get(h["path_id"], "")
    b = bucket_of(path)
    bucket_total[b] += h["count"]
    byday[d] += h["count"]
    cat = catf(refs.get(h["ref_id"], ""))
    if cat == "Search":
        byday_search[d] += h["count"]
    refcat[cat] += h["count"]
    bypath[h["path_id"]] += h["count"]

toppages = sorted(((paths.get(pid, ""), c) for pid, c in bypath.items()),
                  key=lambda x: -x[1])[:12]
byloc = collections.Counter()
for l in locs:
    if l.get("path_id") in BOT_PIDS:                    # keep scanner tokens out of geo
        continue
    byloc[l["location"]] += l["count"]
toploc = byloc.most_common(15)

# ── Fold in GitHub repo traffic: VIEWS join reach + referrers; CLONES stay a
#    separate developer-signal stat. Use the ACCUMULATED daily views (every day
#    we've snapshotted, kept past GitHub's 14-day purge) — NOT the 14-day rolling
#    `count` — so total reach is cumulative and never drops as launch days age
#    out of the trailing window. (Only explicitly-rolling stats may decrease.)
repo_views = {}
for key, r in repo_traffic.items():
    vdays = r.get("views", {}).get("days", [])
    repo_views[key] = sum(d.get("count", 0) for d in vdays) if vdays \
        else r.get("views", {}).get("count", 0)         # fall back to 14d if no history yet
    for rf in r.get("referrers", []):                  # merge repo referrers into chart
        refcat[catf(rf["referrer"])] += rf["count"]

repo_views_total = sum(repo_views.values())
reach_bucket = collections.Counter()                   # Pages real + repo views / project
for key, _l, _p, _c in BUCKETS:
    reach_bucket[key] = bucket_total.get(key, 0) + repo_views.get(key, 0)
reach_total = pages_real + repo_views_total            # the headline number
total = reach_total                                    # pct() denominator

top_bucket = max((k for k, _l, _p, _c in PROJECTS), key=lambda k: reach_bucket[k],
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
        stars_svg = _svg.read()


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
.post{background:var(--panel);border:1px solid var(--bd);border-radius:16px;padding:18px 20px;margin-bottom:12px;transition:border-color .15s}
.post:hover{border-color:var(--border-hi,rgba(122,165,242,.45))}
.post-hd{display:flex;align-items:center;gap:10px;margin-bottom:9px;font-size:13px;color:var(--mut)}
.post-hd .date{margin-left:auto;color:var(--mut2);font-size:12.5px}
.li-chip{display:inline-flex;align-items:center;gap:5px;background:#0a66c2;color:#fff;font-size:11px;font-weight:700;padding:3px 8px 3px 6px;border-radius:5px}
.li-chip b{background:#fff;color:#0a66c2;border-radius:2px;padding:0 3px;font-size:10.5px;line-height:1.4}
.post-title{font-size:16.5px;font-weight:700;color:var(--tx);text-decoration:none;line-height:1.35;display:inline-block}
.post-title:hover{color:var(--ac2);text-decoration:underline}
.post-stats{display:flex;gap:30px;margin:15px 0 12px;flex-wrap:wrap}
.post-stats .st b{display:block;font-size:21px;font-weight:700;color:var(--ac2);line-height:1.05;letter-spacing:-.01em}
.post-stats .st span{font-size:11.5px;color:var(--mut)}
.post-eng{font-size:13px;color:var(--mut);display:flex;gap:18px;flex-wrap:wrap;border-top:1px solid var(--bd);padding-top:11px}
.post-eng b{color:var(--tx);font-weight:600}
@media(max-width:680px){.cards{grid-template-columns:repeat(2,1fr)}.rl{flex-basis:120px}.post-stats{gap:20px}}"""


def bar(label, val, vmax, sub="", color="#5b8def"):
    w = max(2, round(val / vmax * 100)) if vmax else 2
    return (f'<div class="row"><span class="rl">{label}</span>'
            f'<span class="rbar"><i style="width:{w}%;background:{color}"></i></span>'
            f'<span class="rv">{val}{(" · " + sub) if sub else ""}</span></div>')


def esc(s):
    """Minimal XML-text escape for values injected into SVG <text>/<title> nodes."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cumulative_svg(points, color="#37c2f0", markers=None, height=180, unit=""):
    """Cumulative-total 'glamour' line chart (no JS): a running sum of a daily
    series, so the line only ever goes up. Area-filled, endpoint total labelled,
    optional amber milestone markers, per-point hover. No bars, no moving average.

      points  : [(date 'YYYY-MM-DD', daily_value)] ascending
      markers : [(date 'YYYY-MM-DD', label)]
    """
    import math
    pts = [(d, v) for d, v in points if v is not None]
    if len(pts) < 2:
        return ""
    cum, run = [], 0
    for d, v in pts:
        run += v
        cum.append((d, run))
    markers = sorted((m for m in (markers or []) if m and m[0]), key=lambda m: m[0])
    W, H = 720, height
    x0, x1, y0, y1 = 40, W - 12, 24, H - 22
    d0 = datetime.date.fromisoformat(cum[0][0])
    dN = datetime.date.fromisoformat(cum[-1][0])
    for _md, _lbl in markers:
        try:
            _mdt = datetime.date.fromisoformat(_md)
        except ValueError:
            continue
        if dN < _mdt <= dN + datetime.timedelta(days=7):
            dN = _mdt
    span = max((dN - d0).days, 1)
    sx = lambda ds: x0 + (x1 - x0) * (datetime.date.fromisoformat(ds) - d0).days / span
    vmax = cum[-1][1] or 1                       # monotonic: the last point is the max
    raw = vmax / 5
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    nmax = math.ceil(vmax / step) * step
    ticks, _t = [], 0.0
    while _t <= nmax + 1e-6:
        ticks.append(int(round(_t)))
        _t += step
    ticks = sorted(set(ticks))
    sy = lambda v: y1 - (y1 - y0) * (v / nmax)

    svg = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
           f'style="display:block;font-family:Inter,system-ui,sans-serif">']
    svg.append('<style>.col .hit{fill:transparent}.col:hover .hit{fill:rgba(255,255,255,.05)}'
               '.col .tip{opacity:0;transition:opacity .1s}.col:hover .tip{opacity:1}'
               '.tip{pointer-events:none}</style>')
    for t in ticks:
        gy = sy(t)
        svg.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" '
                   f'stroke="var(--bd)" stroke-width="1" opacity="{0.85 if t == 0 else 0.33}"/>')
        svg.append(f'<text x="{x0 - 6}" y="{gy + 3:.1f}" fill="var(--mut2)" '
                   f'font-size="9" text-anchor="end">{t:,}</text>')
    svg.append(f'<text x="{x0}" y="{H - 5}" fill="var(--mut)" font-size="10">{cum[0][0]}</text>')
    svg.append(f'<text x="{x1}" y="{H - 5}" fill="var(--mut)" font-size="10" '
               f'text-anchor="end">{cum[-1][0]}</text>')
    line = "M " + " L ".join(f"{sx(d):.1f} {sy(v):.1f}" for d, v in cum)
    svg.append(f'<path d="{line} L {sx(cum[-1][0]):.1f} {y1:.1f} L {x0:.1f} {y1:.1f} Z" '
               f'fill="{color}" opacity="0.13"/>')
    last_lx = -999
    for md, ml in markers:
        try:
            mx = sx(md)
        except ValueError:
            continue
        if not (x0 - 1 <= mx <= x1 + 1):
            continue
        svg.append(f'<line x1="{mx:.1f}" y1="{y0 - 6:.1f}" x2="{mx:.1f}" y2="{y1:.1f}" '
                   f'stroke="#e0a52e" stroke-width="1" stroke-dasharray="2 3" opacity="0.5"/>')
        svg.append(f'<path d="M {mx - 3:.1f} {y0 - 9:.1f} L {mx + 3:.1f} {y0 - 9:.1f} '
                   f'L {mx:.1f} {y0 - 3:.1f} Z" fill="#e0a52e"><title>{esc(ml)} · {md}</title></path>')
        if mx - last_lx > 30:
            svg.append(f'<text x="{mx:.1f}" y="{y0 - 12:.1f}" fill="#e0a52e" font-size="9" '
                       f'font-weight="600" text-anchor="middle">{esc(ml)}</text>')
            last_lx = mx
    svg.append(f'<path d="{line}" fill="none" stroke="{color}" stroke-width="2.4" '
               f'stroke-linejoin="round" stroke-linecap="round"/>')
    ld, lv = cum[-1]
    svg.append(f'<circle cx="{sx(ld):.1f}" cy="{sy(lv):.1f}" r="3.6" fill="{color}"/>')
    svg.append(f'<text x="{sx(ld) - 7:.1f}" y="{sy(lv) - 7:.1f}" fill="var(--tx)" '
               f'font-size="13" font-weight="700" text-anchor="end">{lv:,}{unit}</text>')
    slot = (x1 - x0) / span
    hitw = max(slot, 6)
    for d, v in cum:
        cx = sx(d)
        txt = f'{d} · {v:,}{unit} total'
        tw = len(txt) * 6.0 + 14
        tx = min(max(cx, x0 + tw / 2), x1 - tw / 2)
        ty = max(sy(v) - 10, y0 + 16)
        svg.append('<g class="col">'
                   f'<rect class="hit" x="{cx - hitw / 2:.1f}" y="{y0}" '
                   f'width="{hitw:.1f}" height="{y1 - y0}"/>'
                   f'<g class="tip"><rect x="{tx - tw / 2:.1f}" y="{ty - 14:.1f}" '
                   f'width="{tw:.1f}" height="17" rx="4" fill="#0f1830" '
                   f'stroke="var(--bd)" stroke-width="1"/>'
                   f'<text x="{tx:.1f}" y="{ty - 2:.1f}" text-anchor="middle" '
                   f'fill="var(--tx)" font-size="11">{esc(txt)}</text></g></g>')
    svg.append("</svg>")
    return "".join(svg)


def total_block(P, title, sub, daily_points, color, markers, unit):
    """Append a cumulative-total 'glamour' chart section (running sum, up only)."""
    svg = cumulative_svg(daily_points, color=color, markers=markers, unit=unit)
    if not svg:
        return
    P.append(f'<h2>{title}</h2>')
    P.append(f'<div class="sec" style="padding:16px 18px 10px">'
             f'<div style="font-size:12.5px;font-weight:600;color:var(--tx);'
             f'margin:0 0 8px">{sub}</div>{svg}'
             f'<p class="sub" style="margin:8px 0 0;font-size:12.5px">'
             f'<b style="color:{color}">━</b> cumulative total &nbsp;·&nbsp; '
             f'<b style="color:#e0a52e">▲</b> milestone.</p></div>')


def trend_svg(points, color="#37c2f0", markers=None, avg_window=7,
              height=180, unit=""):
    """Self-contained inline-SVG trend chart for a daily time-series (no JS).

    Reusable for any daily series (PyPI downloads, pageviews, …). Draws per-day
    BARS against a labelled, round-number y-axis so individual daily counts stay
    readable at a glance, a smoothed `avg_window`-day moving-average LINE in `color`
    for the trend, optional amber annotation `markers` (e.g. releases / key dates),
    the latest value labelled, and a per-day <title> for hover read-out.

      points  : [(date 'YYYY-MM-DD', value)] ascending
      markers : [(date 'YYYY-MM-DD', label)]  (e.g. version ships)
    """
    import math
    pts = [(d, v) for d, v in points if v is not None]
    if len(pts) < 2:
        return ""
    # Sort markers chronologically (ISO dates sort lexically) so the left-to-right
    # label-collision logic below works regardless of input order.
    markers = sorted((m for m in (markers or []) if m and m[0]), key=lambda m: m[0])
    W, H = 720, height
    x0, x1, y0, y1 = 40, W - 12, 24, H - 22
    d0 = datetime.date.fromisoformat(pts[0][0])
    dN = datetime.date.fromisoformat(pts[-1][0])
    # Extend the right edge to include a marker at/just past the last data point —
    # e.g. a release tagged today when GitHub's clone traffic still lags a day — but
    # not markers far past the data. (Markers before d0 stay clamped out below.)
    for _md, _lbl in (markers or []):
        try:
            _mdt = datetime.date.fromisoformat(_md)
        except ValueError:
            continue
        if dN < _mdt <= dN + datetime.timedelta(days=7):
            dN = _mdt
    span = max((dN - d0).days, 1)
    sx = lambda ds: x0 + (x1 - x0) * (datetime.date.fromisoformat(ds) - d0).days / span

    # round-number y-axis (~5 ticks) so heights are readable, not just the peak
    vmax = max(v for _, v in pts) or 1
    raw = vmax / 5
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    nmax = math.ceil(vmax / step) * step
    ticks, _t = [], 0.0
    while _t <= nmax + 1e-6:
        ticks.append(int(round(_t)))
        _t += step
    ticks = sorted(set(ticks))          # dedupe (fractional steps on tiny peaks)
    sy = lambda v: y1 - (y1 - y0) * (v / nmax)

    svg = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
           f'style="display:block;font-family:Inter,system-ui,sans-serif">']
    # CSS-only hover: full-column hit target lights up and reveals a styled tooltip
    # (no JS — keeps the page self-contained).
    svg.append('<style>'
               '.col .hit{fill:transparent}'
               '.col:hover .hit{fill:rgba(255,255,255,.05)}'
               '.col .tip{opacity:0;transition:opacity .1s}'
               '.col:hover .tip{opacity:1}'
               '.tip{pointer-events:none}</style>')
    # y gridlines + labels (baseline solid, rest faint)
    for t in ticks:
        gy = sy(t)
        svg.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" '
                   f'stroke="var(--bd)" stroke-width="1" opacity="{0.85 if t == 0 else 0.33}"/>')
        svg.append(f'<text x="{x0 - 6}" y="{gy + 3:.1f}" fill="var(--mut2)" '
                   f'font-size="9" text-anchor="end">{t:,}</text>')
    # first/last date labels
    svg.append(f'<text x="{x0}" y="{H - 5}" fill="var(--mut)" font-size="10">{pts[0][0]}</text>')
    svg.append(f'<text x="{x1}" y="{H - 5}" fill="var(--mut)" font-size="10" '
               f'text-anchor="end">{pts[-1][0]}</text>')
    # per-day bars (the daily counts, readable against the axis) + hover
    slot = (x1 - x0) / span
    bw = max(min(slot * 0.7, 13), 2)
    for d, v in pts:
        bx, by = sx(d), sy(v)
        svg.append(f'<rect x="{bx - bw / 2:.1f}" y="{by:.1f}" width="{bw:.1f}" '
                   f'height="{max(y1 - by, 0):.1f}" rx="1.5" fill="{color}" '
                   f'opacity="0.32"/>')
    # moving-average line (the trend)
    vals = [v for _, v in pts]
    ma = [(d, sum(vals[max(0, i - avg_window + 1):i + 1]) /
              len(vals[max(0, i - avg_window + 1):i + 1]))
          for i, (d, _v) in enumerate(pts)]
    ma_path = "M " + " L ".join(f'{sx(d):.1f} {sy(v):.1f}' for d, v in ma)
    svg.append(f'<path d="{ma_path}" fill="none" stroke="{color}" stroke-width="2.2" '
               f'stroke-linejoin="round" stroke-linecap="round"/>')
    # annotation markers (dashed tick + triangle; label only when it won't collide)
    last_lx = -999
    for md, ml in (markers or []):
        try:
            mx = sx(md)
        except ValueError:
            continue
        if not (x0 - 1 <= mx <= x1 + 1):
            continue
        svg.append(f'<line x1="{mx:.1f}" y1="{y0 - 6:.1f}" x2="{mx:.1f}" y2="{y1:.1f}" '
                   f'stroke="#e0a52e" stroke-width="1" stroke-dasharray="2 3" opacity="0.5"/>')
        svg.append(f'<path d="M {mx - 3:.1f} {y0 - 9:.1f} L {mx + 3:.1f} {y0 - 9:.1f} '
                   f'L {mx:.1f} {y0 - 3:.1f} Z" fill="#e0a52e"><title>{esc(ml)} · {md}</title></path>')
        if mx - last_lx > 30:
            svg.append(f'<text x="{mx:.1f}" y="{y0 - 12:.1f}" fill="#e0a52e" font-size="9" '
                       f'font-weight="600" text-anchor="middle">{esc(ml)}</text>')
            last_lx = mx
    # latest daily value, labelled above its bar
    ld, lv = pts[-1]
    svg.append(f'<text x="{sx(ld):.1f}" y="{sy(lv) - 5:.1f}" fill="var(--tx)" '
               f'font-size="11" font-weight="600" text-anchor="end">{lv:,}</text>')
    # hover layer (topmost): a full-height hit column per day + its CSS tooltip
    hitw = max(slot, 6)
    for d, v in pts:
        cx = sx(d)
        txt = f'{d} · {v:,}{unit}'
        tw = len(txt) * 6.0 + 14
        tx = min(max(cx, x0 + tw / 2), x1 - tw / 2)          # clamp inside plot
        ty = max(sy(v) - 10, y0 + 16)                        # above bar, never clipped
        svg.append('<g class="col">'
                   f'<rect class="hit" x="{cx - hitw / 2:.1f}" y="{y0}" '
                   f'width="{hitw:.1f}" height="{y1 - y0}"/>'
                   f'<g class="tip"><rect x="{tx - tw / 2:.1f}" y="{ty - 14:.1f}" '
                   f'width="{tw:.1f}" height="17" rx="4" fill="#0f1830" '
                   f'stroke="var(--bd)" stroke-width="1"/>'
                   f'<text x="{tx:.1f}" y="{ty - 2:.1f}" text-anchor="middle" '
                   f'fill="var(--tx)" font-size="11">{esc(txt)}</text></g></g>')
    svg.append('</svg>')
    return "".join(svg)


def pct(v):
    return f"{round(v / total * 100)}%" if total else "0%"


P = []
P.append(f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
         f'<meta name="viewport" content="width=device-width, initial-scale=1">'
         f'<title>Community Traffic — Overview</title>'
         # Internal traffic dashboard, not primary content — keep it out of
         # search/GEO indexes (still crawlable via `follow` for any outbound
         # links), and out of sitemap.xml (see that file's header comment).
         f'<meta name="robots" content="noindex, follow">'
         f'<style>{CSS}</style></head>'
         f'<body><div class="wrap">')
P.append('<span class="tag">GoatCounter + GitHub · open-agent-ai-security</span>'
         '<h1>Community Traffic — Overview</h1>')
P.append(f'<p class="sub"><b>Reach</b> combines our hero websites (GoatCounter) '
         f'and GitHub repo traffic, per project, for <b>{days[0]} → {days[-1]}</b>. '
         f'Real traffic only — automated email-campaign hits are tracked separately '
         f'(see <a href="#campaign" style="color:var(--ac2)">Marketo campaign '
         f'tracking</a>), and both sources undercount humans (blockers, no-JS), so '
         f'true reach is if anything higher.</p>')

if IS_SAMPLE:
    P.append('<div class="warn"><b>SAMPLE DATA</b> — no GoatCounter export found, so '
             'this is built-in placeholder data to preview the layout. Drop a real '
             'export into <code>stats/</code> and re-run to replace it.</div>')

# headline cards
P.append('<div class="cards">')
P.append(f'<div class="card"><b>{reach_total:,}</b><span>Total reach</span></div>')
P.append(f'<div class="card"><b>{len(PROJECTS)}</b><span>Projects tracked</span></div>')
P.append(f'<div class="card"><b>{len(days)}</b><span>Days in window</span></div>')
P.append(f'<div class="card"><b>{LABEL.get(top_bucket, "—")}</b>'
         f'<span>Top project</span></div>')
P.append('</div>')

# reach by project (site + repo views, combined into one figure)
P.append('<h2>Reach by project</h2>')
P.append('<p class="sub" style="margin-bottom:8px">Pages-site views and repo '
         'views, combined. Community = the shared root / cross-project pages '
         '(no repo of its own).</p>')
P.append('<div class="sec">')
vmax = max(reach_bucket.values()) if reach_bucket else 0
for key, label, _prefix, color in BUCKETS:
    c = reach_bucket.get(key, 0)
    P.append(bar(f'{label}', c, vmax, sub=pct(c), color=color))
P.append('</div>')

# daily pageviews (site, real only, full window) — key dates as trend markers
P.append('<h2>Daily views — site</h2>')
dv_chart = trend_svg([(d, byday[d]) for d in days], color="#5b8def",
                     markers=[(d, lbl) for d, lbl in key_dates.items()],
                     unit=" views")
if dv_chart:
    P.append(f'<div class="sec" style="padding:16px 18px 10px">'
             f'<div style="font-size:12.5px;font-weight:600;color:var(--tx);'
             f'margin:0 0 8px">Community sites &middot; real views per day</div>{dv_chart}'
             f'<p class="sub" style="margin:8px 0 0;font-size:12.5px">'
             f'<b style="color:#5b8def">━</b> 7-day average &nbsp;·&nbsp; '
             f'<b style="color:#5b8def">▮</b> daily views &nbsp;·&nbsp; '
             f'<b style="color:#e0a52e">▲</b> key date.</p></div>')

# cumulative total REACH (glamour): site views + GitHub repo views, running sum,
# so the endpoint reconciles with the "Total reach" headline card at the top
# (which is also site views + repo views).
_repo_byday = collections.Counter()
for _k, _r in repo_traffic.items():
    _vdays = _r.get("views", {}).get("days", [])
    if _vdays:
        for _x in _vdays:
            _repo_byday[_x["timestamp"][:10]] += _x.get("count", 0)
    elif days:
        # No daily history yet — attribute the 14-day count to the latest day so
        # the cumulative endpoint still matches the headline reach card (which
        # applies the same fallback).
        _repo_byday[days[-1]] += _r.get("views", {}).get("count", 0)
_reach_days = sorted(set(byday) | set(_repo_byday))
total_block(P, "Total reach — all-time",
            "Community sites (views) + GitHub repos &middot; cumulative reach",
            [(d, byday.get(d, 0) + _repo_byday.get(d, 0)) for d in _reach_days], "#5b8def",
            [(d, lbl) for d, lbl in key_dates.items()], "")

# top referrers (site + repo, merged)
P.append('<h2>Top referrers</h2>')
P.append('<p class="sub" style="margin-bottom:8px">Pages-site + repo referrers, '
         'combined.</p><div class="sec">')
rmax = max(refcat.values()) if refcat else 0
for name, c in refcat.most_common(10):
    P.append(bar(name, c, rmax, sub=pct(c), color="#7aa5f2"))
P.append('</div>')

# top pages (site, labelled by project)
P.append('<h2>Top pages — site</h2><div class="sec"><table>')
for path, c in toppages:
    b = bucket_of(path)
    chip = (f'<span class="chip" style="background:{COLOR[b]}22;color:{COLOR[b]}">'
            f'{LABEL[b]}</span>')
    P.append(f'<tr><td>{chip} <code>{path or "/"}</code></td><td class="n">{c}</td></tr>')
P.append('</table></div>')

# geography (site)
P.append('<h2>Top locations — site</h2><div class="sec">')
lmax = toploc[0][1] if toploc else 0
for loc, c in toploc:
    P.append(bar(loc_name(loc), c, lmax, color="#4db6ac"))
P.append('</div>')

# (The "Key social posts" section moved to the LinkedIn stats page — they're all
#  manual LinkedIn posts; see stats/make_linkedin.py → linkedin.html.)

# GitHub stars (counts fetched live; combined trend chart from star-history.com)
P.append('<h2>GitHub stars</h2>')
P.append('<p class="sub">A GitHub <b>star</b> is a public bookmark — a developer '
         'flagging a project they find useful or want to follow. It\'s the '
         'open-source equivalent of a &ldquo;like,&rdquo; and the running total is '
         'the standard rough proxy for a project\'s mindshare and momentum. Live '
         'counts per project below, with the combined trend over time.</p>')
P.append('<div class="cards" style="grid-template-columns:repeat(2,1fr)">')
for key, label, _prefix, color in PROJECTS:
    if key in REPO:
        n = stars.get(key)
        val = f'&#9733; {n:,}' if n is not None else '&mdash;'
        P.append(f'<div class="card"><b style="color:{color}">{val}</b>'
                 f'<span>{label} &middot; <code>{REPO[key]}</code></span></div>')
P.append('</div>')
if stars_svg:
    P.append(f'<div class="sec" style="padding:16px 18px 12px;overflow:hidden">{stars_svg}</div>')
    P.append('<p class="sub" style="margin:10px 0 0">Cumulative stargazers from the '
             'GitHub API. '
             'A launch is a spike; the slope over the following weeks is the real adoption signal.</p>')

# PyPI downloads (pip installs; accumulated daily, all-inclusive; observra only)
if pypi_dl:
    pypi_labels = [label for key, label, _p, _c in PROJECTS
                   if key in PYPI and key in pypi_dl]
    P.append(f'<h2>PyPI downloads &middot; {", ".join(pypi_labels)}</h2>')
    P.append('<p class="sub"><b style="color:var(--tx)">Observra only.</b> Installs of '
             'the <code>observra</code> Python package via <code>pip</code>, from the '
             'public pypistats.org dataset — Praxen ships as a Claude Code / Codex '
             'plugin, not a pip package, so it has no PyPI footprint. Counts are '
             'all-inclusive (they include CI and mirror pulls), so the smoothed line, '
             'not any single spiky day, is the signal.</p>')
    for key, label, _prefix, color in PROJECTS:
        if key not in PYPI or key not in pypi_dl:
            continue
        dl = sorted(pypi_dl[key].get("days", []), key=lambda d: d["date"])
        n = [d["downloads"] for d in dl]
        tot, last_30, last_7 = sum(n), sum(n[-30:]), sum(n[-7:])
        P.append('<div class="cards" style="grid-template-columns:repeat(3,1fr)">')
        for val, cap in ((last_30, f"{label} &middot; last 30 days"),
                         (last_7, "last 7 days"),
                         (tot, "tracked total")):
            P.append(f'<div class="card"><b style="color:{color}">{val:,}</b>'
                     f'<span>{cap}</span></div>')
        P.append('</div>')
        chart = trend_svg([(d["date"], d["downloads"]) for d in dl], color=color,
                          markers=[(r["date"], r["version"])
                                   for r in pypi_dl[key].get("releases", [])],
                          unit=" downloads")
        if chart:
            P.append(f'<div class="sec" style="padding:16px 18px 10px">'
                     f'<div style="font-size:12.5px;font-weight:600;color:var(--tx);'
                     f'margin:0 0 8px"><b style="color:{color}">{label}</b> '
                     f'<code>{PYPI[key]}</code> &middot; downloads per day</div>{chart}'
                     f'<p class="sub" style="margin:8px 0 0;font-size:12.5px">'
                     f'<b style="color:{color}">━</b> 7-day average &nbsp;·&nbsp; '
                     f'<b style="color:{color}">▮</b> daily downloads &nbsp;·&nbsp; '
                     f'<b style="color:#e0a52e">▲</b> version ship.</p></div>')
        # cumulative total installs (glamour)
        total_block(P, f"Total installs — {label}",
                    f"{label} &middot; cumulative <code>pip</code> downloads",
                    [(d["date"], d["downloads"]) for d in dl], color,
                    [(r["date"], r["version"]) for r in pypi_dl[key].get("releases", [])],
                    " downloads")

# Praxen plugin installs (proxy: GitHub repo clones — Claude Code / Codex install
# by git-cloning the repo; there is no official marketplace download counter).
_prx = repo_traffic.get("praxen", {}) or {}
_prx_cl = _prx.get("clones", {}) or {}
_prx_rel = _prx.get("releases", [])            # tagged releases → milestone markers
prx_days = sorted(({"date": d["timestamp"][:10], "count": d["count"]}
                   for d in _prx_cl.get("days", [])), key=lambda d: d["date"])
if prx_days:
    color = COLOR.get("praxen", "#ff7a2e")
    n = [d["count"] for d in prx_days]
    tot, last_30, last_7 = sum(n), sum(n[-30:]), sum(n[-7:])
    uniq_14 = _prx_cl.get("uniques", 0)          # GitHub's dedup'd 14-day unique cloners
    P.append('<h2>Praxen plugin installs</h2>')
    P.append('<p class="sub"><b style="color:var(--tx)">Praxen only.</b> Praxen '
             'installs as an agent plugin (Claude Code / Codex), and those '
             'marketplaces expose no public download counter — so we use '
             '<b>GitHub repo clones as a proxy for installs</b> '
             f'(<b style="color:{color}">{uniq_14:,} unique installs</b> in the '
             'trailing 14 days, GitHub-deduplicated). It is a proxy: the count also '
             'includes update re-pulls and CI, so — like the PyPI numbers — read the '
             'trend, not an exact headcount. (Observra ships on PyPI, hence its '
             'different install signal.)</p>')
    P.append('<div class="cards" style="grid-template-columns:repeat(3,1fr)">')
    for val, cap in ((last_30, "Praxen &middot; installs, last 30 days"),
                     (last_7, "installs, last 7 days"),
                     (tot, "tracked total installs")):
        P.append(f'<div class="card"><b style="color:{color}">{val:,}</b>'
                 f'<span>{cap}</span></div>')
    P.append('</div>')
    # Markers: Praxen's own tagged releases (future-proof — they auto-appear as new
    # tags land in the window) plus only Praxen-relevant key dates (its launch), not
    # Observra's, which is irrelevant to Praxen installs.
    prx_marks = [(r["date"], r["tag"]) for r in _prx_rel]
    prx_marks += [(d, lbl) for d, lbl in key_dates.items() if "praxen" in lbl.lower()]
    chart = trend_svg([(d["date"], d["count"]) for d in prx_days], color=color,
                      markers=prx_marks, unit=" installs")
    if chart:
        P.append(f'<div class="sec" style="padding:16px 18px 10px">'
                 f'<div style="font-size:12.5px;font-weight:600;color:var(--tx);'
                 f'margin:0 0 8px"><b style="color:{color}">Praxen</b> '
                 f'<code>open-agent-ai-security/praxen</code> &middot; installs per day '
                 f'(clone proxy)</div>{chart}'
                 f'<p class="sub" style="margin:8px 0 0;font-size:12.5px">'
                 f'<b style="color:{color}">━</b> 7-day average &nbsp;·&nbsp; '
                 f'<b style="color:{color}">▮</b> daily installs &nbsp;·&nbsp; '
                 f'<b style="color:#e0a52e">▲</b> release / launch.</p></div>')
    # cumulative total installs (glamour)
    total_block(P, "Total installs — Praxen", "Praxen &middot; cumulative plugin installs "
                "(clone proxy)",
                [(d["date"], d["count"]) for d in prx_days], color, prx_marks, " installs")

# Marketo campaign tracking (ongoing — each detected send is logged as it lands)
_bot = CLASS["campaign_bot"]
_hum = CLASS["campaign_human"]
_camp = _hum + _bot
if _camp:
    _ctr = (100 * _hum / _camp) if _camp else 0
    P.append('<h2 id="campaign">Marketo campaign tracking</h2>')
    P.append(f'<p class="sub" style="margin-bottom:8px">Marketing email blasts are '
             f'<b>auto-detected</b> here whenever tokenized email traffic '
             f'(Marketo <code>mkt_tok</code> links) spikes past <b>{BURST_MIN} '
             f'hits/hour</b>. Almost all of that volume is corporate email-security '
             f'infrastructure (Microsoft Safe Links, Mimecast, Proofpoint, …) '
             f'auto-fetching every link — not people — so we hold it out of the '
             f'reach figures above and log each send\'s real human click-through '
             f'below. New campaigns append here as they land.</p>')
    # one row per detected campaign (send day)
    P.append('<div class="sec"><table>')
    P.append('<tr><td>Detected campaign</td><td class="n">Tracked</td>'
             '<td class="n">Human</td><td class="n">Scanners</td>'
             '<td class="n">CTR</td></tr>')
    for cd in CAMPAIGN_DAYS:
        ch, cbt = CAMP_BY_DAY[cd]["human"], CAMP_BY_DAY[cd]["bot"]
        ct = ch + cbt
        cr = (100 * ch / ct) if ct else 0
        P.append(f'<tr><td>📧 <b style="color:var(--tx)">{cd}</b> · Marketo blast</td>'
                 f'<td class="n">{ct:,}</td><td class="n">{ch:,}</td>'
                 f'<td class="n">{cbt:,}</td><td class="n">{cr:.1f}%</td></tr>')
    if len(CAMPAIGN_DAYS) > 1:
        P.append(f'<tr><td style="color:var(--tx)"><b>All campaigns</b></td>'
                 f'<td class="n">{_camp:,}</td><td class="n">{_hum:,}</td>'
                 f'<td class="n">{_bot:,}</td><td class="n">{_ctr:.1f}%</td></tr>')
    P.append('</table></div>')
    # human vs scanner split across all detected campaigns
    P.append('<div class="sec">')
    cmax = max(_hum, _bot, 1)
    P.append(bar("Human click-throughs (est.)", _hum, cmax,
                 sub=f"{_ctr:.1f}%", color="#5b8def"))
    P.append(bar("Automated scanner fetches", _bot, cmax,
                 sub=f"{100-_ctr:.1f}%", color="#c65d5d"))
    P.append('</div>')
    P.append(f'<p class="sub" style="margin-top:10px">A <b>~{_ctr:.1f}%</b> '
             f'human-signal rate — recipients showing a mobile viewport or a '
             f'time-separated revisit — is a healthy click-through for a B2B email '
             f'send; the rest is unavoidable scanner traffic every blast generates. '
             f'How each pageview is attributed (Marketo token &rarr; mobile / '
             f'revisit / burst-hour screen) is documented at the top of '
             f'<code>stats/generate.py</code>.</p>')

# search-driven traffic (referrer = a search engine) — the TREND is the point.
# The SEO/GEO milestone marks when that work went live. trend_svg extends the
# right edge to show a marker up to 7 days past the last data day, then clamps it
# off once the data lags further behind — so as fresh exports arrive it settles
# into place and marks where organic-search indexing begins to compound.
SEO_MILESTONE = ("2026-07-15", "SEO/GEO live")
sd_chart = trend_svg([(d, byday_search[d]) for d in days], color="#3fb98f",
                     markers=[SEO_MILESTONE], unit=" search views")
if sd_chart:
    P.append('<h2>Search-driven traffic</h2>')
    P.append('<p class="sub" style="margin-bottom:8px">Views whose referrer is a '
             'search engine (Google, Bing, DuckDuckGo, Brave, …). Like all referrer '
             'data this <b>undercounts</b> — many search visits arrive with no '
             'referrer — so read the <b>trend</b>, not the absolute level. The '
             'marker is when the SEO/GEO work went live; organic search indexes and '
             'compounds over weeks, so lift shows up after it, not immediately.</p>')
    P.append(f'<div class="sec" style="padding:16px 18px 10px">'
             f'<div style="font-size:12.5px;font-weight:600;color:var(--tx);'
             f'margin:0 0 8px">Community sites &middot; views referred by a search '
             f'engine, per day</div>{sd_chart}'
             f'<p class="sub" style="margin:8px 0 0;font-size:12.5px">'
             f'<b style="color:#3fb98f">━</b> 7-day average &nbsp;·&nbsp; '
             f'<b style="color:#3fb98f">▮</b> daily search views &nbsp;·&nbsp; '
             f'<b style="color:#e0a52e">▲</b> SEO/GEO work live.</p></div>')

P.append(f'<p class="foot">Generated {today} by <code>stats/generate.py</code>. '
         f'Sources: GoatCounter export (Pages sites, community account)'
         f'{" — SAMPLE placeholder data" if IS_SAMPLE else ""} &middot; GitHub repo '
         f'traffic API (repo views/clones, 14-day window) &middot; stars via GitHub '
         f'API. <b>Reach ({reach_total:,})</b> = {pages_real:,} real site views '
         f'({days[0]}→{days[-1]}) + {repo_views_total:,} repo views (accumulated '
         f'daily, kept past GitHub\'s 14-day purge); a further {CLASS["campaign_bot"]:,} automated '
         f'email-campaign scanner pageviews were tracked separately (see Marketo '
         f'campaign tracking). Method documented in <code>stats/generate.py</code>.</p>')
P.append('</div></body></html>')

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("".join(P))

kind = "SAMPLE" if IS_SAMPLE else "real export"
print(f"Wrote {OUT}")
print(f"  {kind}: REACH {reach_total:,} = {pages_real:,} site ({days[0]}→{days[-1]})"
      f" + {repo_views_total:,} repo (GitHub, accumulated)")
for key, label, _prefix, _color in BUCKETS:
    print(f"  {label:<12} reach {reach_bucket.get(key, 0):>6,}"
          f"  (site {bucket_total.get(key,0):,} + repo {repo_views.get(key,0):,})")
print(f"  campaigns: {', '.join(CAMPAIGN_DAYS) or '—'}"
      f"  (human {CLASS['campaign_human']:,} / scanners {CLASS['campaign_bot']:,})")
print("  stars: " + ", ".join(f"{LABEL[k]} {v if v is not None else '—'}" for k, v in stars.items()))

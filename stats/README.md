<!--
  Copyright 2026 Exabeam, Inc.
  SPDX-License-Identifier: Apache-2.0
-->

# stats/ — community traffic

Standing, **overall** traffic tracking for the Open Agent and AI Security
Community Pages sites. One rolled-up community view, then a per-project
breakout (currently Praxen and Observra — more as they launch).

This is intentionally different from **Praxen's** `stats/` (in the praxen repo),
which is a one-time, **launch** retrospective. This one is the ongoing "how is
traffic doing across everything" dashboard.

| File | What it is |
|---|---|
| `generate.py` | The generator. Reads a GoatCounter export → writes `index.html`. |
| `index.html` | The self-contained report, served at `/stats/`. Regenerated, not hand-edited. |
| `community-stars.svg` | Combined star-history.com chart (both repos), embedded inline. Refresh via `curl` (below). |
| `make_linkedin.py` | Generator for the **separate** LinkedIn page. Reads three manual `.xls` exports → writes `linkedin.html`. See [LinkedIn Community stats](#linkedin-community-stats-separate-page). |
| `linkedin.html` | The self-contained LinkedIn report. Regenerated, not hand-edited. Its own page — not linked from the main dashboard yet. |

## How the breakout works

Every community Pages site reports to **one shared GoatCounter account**
(`open-agent-ai-security`), so a single export contains every path. The
generator buckets each path by prefix:

- `/praxen/*` → **Praxen**
- `/observra/*` → **Observra**
- everything else (`/`, shared pages) → **Community**

**Add a project** by appending one row to `PROJECTS` at the top of
`generate.py`:

```python
PROJECTS = [
    ("praxen",   "Praxen",   "/praxen",   "#ff7a2e"),
    ("observra", "Observra", "/observra", "#37c2f0"),
    ("newproj",  "NewProj",  "/newproj",  "#a06bff"),   # ← new
]
# ...and, for the GitHub-stars section, its repo:
REPO = {
    "praxen":   "open-agent-ai-security/praxen",
    "observra": "open-agent-ai-security/observra",
    "newproj":  "open-agent-ai-security/newproj",       # ← new
}
```

The **GitHub stars** section shows a live stargazer count per project (fetched
from the GitHub API at build time; shows `—` if offline) plus a combined
star-history trend chart. Add the repo to `community-stars.svg` when you refresh
it (see below).

## Data source

| Source | What it gives | How captured |
|---|---|---|
| **GoatCounter export** (`open-agent-ai-security` account) | Pageviews, referrers, geography, top pages — for the whole community | GoatCounter → Settings → Export → download, unzip into `stats/` (`goatcounter-export*/`). **Not committed** (per-account analytics — keep local). |

> Note: GoatCounter is one half of a temporary GoatCounter/Cloudflare A/B and
> undercounts (blockers, no-JS), so true Pages traffic is higher. GitHub **repo**
> traffic (stars, clones, views) is a separate property (each repo's own
> Insights) and is **not** rolled in here.

## Regenerate

```bash
# 1. Download a fresh export from GoatCounter and unzip it into stats/
#    (creates stats/goatcounter-export.../ — gitignored, keep local).

# 2. (optional) refresh the combined star-history chart.
curl -sL "https://api.star-history.com/svg?repos=open-agent-ai-security/praxen,open-agent-ai-security/observra&type=Date" \
  -o stats/community-stars.svg

# 3. Build the report (fetches live star counts from the GitHub API).
python3 stats/generate.py
```

With **no export present**, `generate.py` renders from built-in **SAMPLE** data
(clearly marked in the report) so the layout can be previewed before real data
exists — that's the current committed state of the scaffolding.

To make a PDF for emailing (not committed — regenerate on demand):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --no-pdf-header-footer --print-to-pdf=stats/community-traffic.pdf \
  "file://$PWD/stats/index.html"
```

## LinkedIn Community stats (separate page)

`linkedin.html` is a **companion** page for the [LinkedIn company page](https://www.linkedin.com/company/open-agent-and-ai-security-community/)
— audience, content, and page-visitor stats. It is **deliberately kept separate**
from the main Community Traffic dashboard (its own page, not in the nav) until
there's enough history to be worth folding in. Same house style as `generate.py`,
accent retinted LinkedIn blue.

**Why it's manual:** LinkedIn has no analytics API on our plan yet, so — exactly
like the pre-automation GoatCounter baseline — the page is fed by hand-exported
`.xls` reports and refreshed weekly-ish. When API access lands, this becomes an
automated feed.

### The three exports

From the company page → **Analytics**, export each tab. LinkedIn emits old-BIFF
`.xls`, each suffixed with a millisecond timestamp:

| Tab → file | What it gives |
|---|---|
| **Followers** (`*_followers_*.xls`) | New-followers time series + follower demographics (seniority, industry, company size, location, job function) |
| **Content** (`*_content_*.xls`) | Post-impressions time series + per-post engagement (`All posts` sheet) |
| **Visitors** (`*_visitors_*.xls`) | Page-view traffic (desktop/mobile, unique) + visitor demographics |

These are three **different** dimensions (audience / content / traffic), not
supersets of each other — together they form a reach → visits → follows funnel.

### Regenerate

```bash
# 1. Export all three tabs; drop the .xls files into stats/linkedin-exports/
#    (gitignored — raw exports are local inputs, only linkedin.html is committed).
#    The generator auto-picks the NEWEST of each type by timestamp, so you can
#    just keep dropping fresh files in.

# 2. One-time: install the only non-stdlib dependency (reads LinkedIn's .xls).
python3 -m pip install xlrd

# 3. Build the page, then commit the regenerated stats/linkedin.html.
python3 stats/make_linkedin.py
```

### What the page shows (all derived from the exports — nothing hand-entered)

- Headline cards + a **reach → visits → follows** signal strip (labeled as
  separate LinkedIn surfaces, not a strict subset).
- **Cumulative total-followers line chart** with a "page live" launch marker —
  the LinkedIn analog of the GitHub-stars chart.
- Full **follower** and **visitor** demographics — every bucket its own bar (no
  rollups); long lists pack in a masonry grid.
- Per-post cards (Top-reach / Best-rate / Video badges, linked to each post).
- Stacked **desktop vs mobile** daily page-views chart.

All numbers, the date window, the active-day count, y-axis scaling, and the
launch-marker placement are computed from the data, so it keeps working as the
history grows past the launch week.

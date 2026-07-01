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
```

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

# 2. Build the report.
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

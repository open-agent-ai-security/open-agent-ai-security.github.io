#!/usr/bin/env python3
# Copyright 2026 Exabeam, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Generate stats/linkedin.html from the manual LinkedIn analytics exports.

LinkedIn's org analytics has no public API on our plan yet, so the community page
is fed by hand-exported .xls reports — three of them, downloaded together from the
page's Analytics tabs:

    *_followers_<ts>.xls   audience   — new-followers time series + demographics
    *_content_<ts>.xls     content    — post engagement time series + per-post
    *_visitors_<ts>.xls    visitors   — page-view traffic + visitor demographics

Drop the latest set into stats/linkedin-exports/ (gitignored) and run:

    python3 stats/make_linkedin.py

It writes a self-contained stats/linkedin.html — same house style as the main
Community Traffic dashboard (generate.py), accent retinted LinkedIn blue, kept as
its own page. Weekly-ish cadence: re-export, drop in, re-run, commit linkedin.html.

Only dependency beyond the stdlib is `xlrd` (reads the old-BIFF .xls LinkedIn
emits): `python3 -m pip install xlrd`.
"""
import os, sys, re, glob, json, math, argparse, datetime, html

try:
    import xlrd
except ImportError:
    sys.exit("this script needs xlrd to read LinkedIn's .xls exports:\n"
             "    python3 -m pip install xlrd")

HERE = os.path.dirname(os.path.abspath(__file__))
LI_BLUE = "#0a66c2"

# ── low-level xls helpers ────────────────────────────────────────────────────
def _newest(indir, kind):
    """Most recently modified export of a given kind in `indir`.

    LinkedIn names each file <slug>_<kind>_<timestamp>.xls; we pick by mtime
    (newest download wins) rather than parsing the name, so a rename or a
    differently-shaped timestamp can't shadow the actual latest file.
    """
    hits = set(glob.glob(os.path.join(indir, f"*_{kind}_*.xls"))) | \
           set(glob.glob(os.path.join(indir, f"*{kind}*.xls")))
    if not hits:
        return None
    return max(hits, key=os.path.getmtime)


def _header_row(sheet):
    """Index of the row whose first cell is 'Date' (time-series sheets carry a
    description line above the header); 0 for the demographic sheets."""
    for r in range(min(6, sheet.nrows)):
        if str(sheet.cell_value(r, 0)).strip().lower() == "date":
            return r
    return 0


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _pdate(s):
    """Parse LinkedIn's text dates (MM/DD/YYYY)."""
    try:
        return datetime.datetime.strptime(str(s).strip(), "%m/%d/%Y").date()
    except ValueError:
        return None


def _cell(sheet, r, c):
    """cell_value with an out-of-range guard — LinkedIn could drop/reorder a
    column, and we'd rather read a blank than crash the whole run."""
    return sheet.cell_value(r, c) if c < sheet.ncols else ""


def _row_date(sheet, r):
    """Date in column 0, whether LinkedIn stored it as MM/DD/YYYY text (current)
    or a native Excel date serial (defensive — would otherwise silently drop
    every row and emit an all-zero page)."""
    if sheet.cell_type(r, 0) == xlrd.XL_CELL_DATE:
        try:
            return xlrd.xldate_as_datetime(
                sheet.cell_value(r, 0), sheet.book.datemode).date()
        except Exception:
            return None
    return _pdate(sheet.cell_value(r, 0))


def series(sheet, *cols):
    """[(date, v_col0, v_col1, ...)] for each dated row, in sheet order."""
    h = _header_row(sheet)
    out = []
    for r in range(h + 1, sheet.nrows):
        d = _row_date(sheet, r)
        if d is None:
            continue
        out.append((d,) + tuple(_num(_cell(sheet, r, c)) for c in cols))
    return out


def demographic(sheet):
    """[(label, count)] from a two-column demographic sheet (header on row 0),
    sorted by count descending (stable — ties keep sheet order)."""
    if sheet.ncols < 2:
        return []
    rows = [(str(sheet.cell_value(r, 0)).strip(), _num(sheet.cell_value(r, 1)))
            for r in range(1, sheet.nrows) if str(sheet.cell_value(r, 0)).strip()]
    return sorted(rows, key=lambda kv: -kv[1])


def _clean_place(label):
    """LinkedIn double-suffixes some regions ('…, Canada, Canada'); collapse."""
    parts = [p.strip() for p in label.split(",")]
    while len(parts) >= 2 and parts[-1] == parts[-2]:
        parts.pop()
    return ", ".join(parts)


# ── html/svg building blocks ─────────────────────────────────────────────────
def esc(s):
    return html.escape(str(s), quote=True)


def safe_url(u):
    """Only let http/https/mailto links from the export reach an href — the
    report is published publicly, so a stray javascript:/data: URL in an export
    cell must not become a live scheme."""
    u = str(u).strip()
    return u if u.lower().startswith(("http://", "https://", "mailto:")) else "#"


def panel(title, sub, rows, clean=False):
    """A demographic card: every bucket its own full-width bar (no rollups)."""
    mx = max((v for _, v in rows), default=1) or 1
    sub_html = f' <span class="mut">— {esc(sub)}</span>' if sub else ""
    out = ['    <div class="sec">',
           f'      <div class="sec-hd">{esc(title)}{sub_html}</div>']
    for lbl, v in rows:
        label = _clean_place(lbl) if clean else lbl
        w = round(v / mx * 100)
        out.append(f'      <div class="drow"><div class="lab">'
                   f'<span class="l">{esc(label)}</span>'
                   f'<span class="v">{v:.0f}</span></div>'
                   f'<div class="track"><i style="width:{w}%"></i></div></div>')
    out.append('    </div>')
    return "\n".join(out)


def cumulative_line(daily):
    """Inline-SVG cumulative line (total followers over time), styled like the
    main dashboard's trend charts. `daily` = [(date, new_that_day)] ascending."""
    if not daily:
        return ""
    # LinkedIn's export opens weeks before the page had its first follower, so the
    # raw series carries a long flat-at-zero runway (e.g. 06/15 with the first gain
    # on 07/09). Trim the leading zeros, keeping a single zero-day anchor just
    # before the first gain, so the line ramps from 0 instead of starting mid-axis.
    first_gain = next((i for i, (_d, n) in enumerate(daily) if n > 0), None)
    if first_gain and first_gain > 0:
        daily = daily[first_gain - 1:]
    d0, dN = daily[0][0], daily[-1][0]
    span = max((dN - d0).days, 1)
    cum, run = [], 0.0
    for d, n in daily:
        run += n
        cum.append((d, run))
    vmax = max(v for _, v in cum) or 1
    # nice round-number y-axis (~5 ticks), same logic as generate.py:trend_svg
    raw = vmax / 5
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    nmax = math.ceil(vmax / step) * step
    ticks, t = [], 0.0
    while t <= nmax + 1e-6:
        ticks.append(int(round(t)))
        t += step
    W, H, x0, x1, y0, y1 = 720, 180, 40, 708, 24, 158
    sx = lambda d: x0 + (x1 - x0) * (d - d0).days / span
    sy = lambda v: y1 - (y1 - y0) * (v / nmax)

    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
         f'style="display:block;font-family:Inter,system-ui,sans-serif">']
    for tk in ticks:
        gy = sy(tk)
        s.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" '
                 f'stroke="var(--bd)" stroke-width="1" '
                 f'opacity="{0.85 if tk == 0 else 0.33}"/>')
        s.append(f'<text x="{x0 - 6}" y="{gy + 3:.1f}" fill="var(--mut2)" '
                 f'font-size="9" text-anchor="end">{tk:,}</text>')
    s.append(f'<text x="{x0}" y="{H - 5}" fill="var(--mut)" font-size="10">'
             f'{d0.strftime("%m/%d")}</text>')
    s.append(f'<text x="{x1}" y="{H - 5}" fill="var(--mut)" font-size="10" '
             f'text-anchor="end">{dN.strftime("%m/%d")}</text>')
    line = "M " + " L ".join(f"{sx(d):.1f} {sy(v):.1f}" for d, v in cum)
    s.append(f'<path d="{line} L {x1:.1f} {y1:.1f} L {x0:.1f} {y1:.1f} Z" '
             f'fill="var(--ac)" opacity="0.14"/>')
    # launch marker at the first day the count moves off zero
    launch = next((d for (d, n) in daily if n > 0), None)
    if launch and launch > d0:
        mx_ = sx(launch)
        s.append(f'<line x1="{mx_:.1f}" y1="{y0 - 6:.1f}" x2="{mx_:.1f}" '
                 f'y2="{y1:.1f}" stroke="#e0a52e" stroke-width="1" '
                 f'stroke-dasharray="2 3" opacity="0.55"/>')
        s.append(f'<path d="M {mx_ - 3:.1f} {y0 - 9:.1f} L {mx_ + 3:.1f} '
                 f'{y0 - 9:.1f} L {mx_:.1f} {y0 - 3:.1f} Z" fill="#e0a52e">'
                 f'<title>Page live · {launch.strftime("%m/%d")}</title></path>')
        s.append(f'<text x="{mx_:.1f}" y="{y0 - 12:.1f}" fill="#e0a52e" '
                 f'font-size="9" font-weight="600" text-anchor="middle">'
                 f'Page live</text>')
    s.append(f'<path d="{line}" fill="none" stroke="var(--ac2)" '
             f'stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>')
    # dots on days the count grew; label them, thinning out on collision, and
    # always label the final value in bold.
    grew = [(d, v) for (d, v), (_, n) in zip(cum, daily) if n > 0]
    last_lx = -999
    for i, (d, v) in enumerate(grew):
        cx, cy = sx(d), sy(v)
        end = (i == len(grew) - 1)
        s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{3.4 if end else 3}" '
                 f'fill="var(--ac2)"><title>{d.strftime("%m/%d")} · '
                 f'{v:.0f} followers</title></circle>')
        if end or cx - last_lx > 30:
            fill = "var(--tx)" if end else "var(--mut)"
            weight = ' font-weight="700"' if end else ""
            s.append(f'<text x="{cx - 5:.1f}" y="{cy - 6:.1f}" fill="{fill}" '
                     f'font-size="{11.5 if end else 10}"{weight} '
                     f'text-anchor="end">{v:.0f}</text>')
            last_lx = cx
    s.append("</svg>")
    return "".join(s)


def views_trend_svg(rows, avg_window=5):
    """House-style daily page-views chart, matching the main dashboard's
    generate.py:trend_svg: per-day bars against a labelled round-number y-axis,
    a smoothed moving-average trend LINE, first/last date labels, the latest
    value labelled, and a per-day hover tooltip. rows = [(date, total)] ascending.

    avg_window defaults to 5 (not the main chart's 7): the LinkedIn export has
    only a handful of active days, so a 7-day mean would flatten to the window
    average — a 5-day window still tracks the trend."""
    if not any(t > 0 for (_d, t) in rows):
        return ""
    # Trim the export's leading dead-zero runway (LinkedIn's window opens weeks
    # before the first visit), keeping one zero-day anchor before the first
    # active day so the first bar sits on the baseline — same as the followers
    # chart's cumulative_line().
    first = next(i for i, r in enumerate(rows) if r[1] > 0)
    rows = rows[max(0, first - 1):]
    pts = list(rows)
    d0, dN = rows[0][0], rows[-1][0]
    span = max((dN - d0).days, 1)
    W, H, x0, x1, y0, y1 = 720, 180, 40, 708, 24, 158
    sx = lambda d: x0 + (x1 - x0) * (d - d0).days / span
    # nice round-number y-axis (~5 ticks), same logic as generate.py:trend_svg
    vmax = max(t for _, t in pts) or 1
    raw = vmax / 5
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    nmax = math.ceil(vmax / step) * step
    ticks, t = [], 0.0
    while t <= nmax + 1e-6:
        ticks.append(int(round(t)))
        t += step
    sy = lambda v: y1 - (y1 - y0) * (v / nmax)

    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
         f'style="display:block;font-family:Inter,system-ui,sans-serif">']
    s.append('<style>.col .hit{fill:transparent}'
             '.col:hover .hit{fill:rgba(255,255,255,.05)}'
             '.col .tip{opacity:0;transition:opacity .1s}'
             '.col:hover .tip{opacity:1}.tip{pointer-events:none}</style>')
    for tk in ticks:
        gy = sy(tk)
        s.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" '
                 f'stroke="var(--bd)" stroke-width="1" '
                 f'opacity="{0.85 if tk == 0 else 0.33}"/>')
        s.append(f'<text x="{x0 - 6}" y="{gy + 3:.1f}" fill="var(--mut2)" '
                 f'font-size="9" text-anchor="end">{tk:,}</text>')
    s.append(f'<text x="{x0}" y="{H - 5}" fill="var(--mut)" font-size="10">'
             f'{d0.strftime("%m/%d")}</text>')
    s.append(f'<text x="{x1}" y="{H - 5}" fill="var(--mut)" font-size="10" '
             f'text-anchor="end">{dN.strftime("%m/%d")}</text>')
    # per-day bars
    slot = (x1 - x0) / span
    bw = max(min(slot * 0.7, 13), 2)
    for d, v in pts:
        bx, by = sx(d), sy(v)
        s.append(f'<rect x="{bx - bw / 2:.1f}" y="{by:.1f}" width="{bw:.1f}" '
                 f'height="{max(y1 - by, 0):.1f}" rx="1.5" fill="var(--ac)" '
                 f'opacity="0.32"/>')
    # moving-average line (the trend)
    vals = [v for _, v in pts]
    ma = [(d, sum(vals[max(0, i - avg_window + 1):i + 1]) /
              len(vals[max(0, i - avg_window + 1):i + 1]))
          for i, (d, _v) in enumerate(pts)]
    ma_path = "M " + " L ".join(f'{sx(d):.1f} {sy(v):.1f}' for d, v in ma)
    s.append(f'<path d="{ma_path}" fill="none" stroke="var(--ac2)" '
             f'stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>')
    # latest daily value, labelled above its bar
    ld, lv = pts[-1]
    s.append(f'<text x="{sx(ld):.1f}" y="{sy(lv) - 5:.1f}" fill="var(--tx)" '
             f'font-size="11" font-weight="600" text-anchor="end">{lv:,.0f}</text>')
    # hover layer (topmost): full-height hit column per day + its CSS tooltip
    hitw = max(slot, 6)
    for d, v in pts:
        cx = sx(d)
        txt = f'{d.strftime("%m/%d")} · {v:,.0f} views'
        tw = len(txt) * 6.0 + 14
        tx = min(max(cx, x0 + tw / 2), x1 - tw / 2)
        ty = max(sy(v) - 10, y0 + 16)
        s.append('<g class="col">'
                 f'<rect class="hit" x="{cx - hitw / 2:.1f}" y="{y0}" '
                 f'width="{hitw:.1f}" height="{y1 - y0}"/>'
                 f'<g class="tip"><rect x="{tx - tw / 2:.1f}" y="{ty - 14:.1f}" '
                 f'width="{tw:.1f}" height="17" rx="4" fill="#0f1830" '
                 f'stroke="var(--bd)" stroke-width="1"/>'
                 f'<text x="{tx:.1f}" y="{ty - 2:.1f}" text-anchor="middle" '
                 f'fill="var(--tx)" font-size="11">{esc(txt)}</text></g></g>')
    s.append("</svg>")
    return "".join(s)


def featured_posts_section():
    """Featured community social posts, moved here from the main /stats dashboard
    (they're all manual LinkedIn posts). Curated in stats/social-posts.json."""
    try:
        posts = json.load(open(os.path.join(HERE, "social-posts.json"),
                               encoding="utf-8")).get("posts", [])
    except (OSError, ValueError):
        return []
    if not posts:
        return []
    out = ['<div style="border-top:1px solid var(--bd);margin:38px 0 0;padding-top:6px">'
           '<span class="tag" style="letter-spacing:.08em">Separate source</span></div>',
           '<h2 style="margin-top:6px">Featured posts</h2>',
           '<p class="sub" style="margin-bottom:10px">A separate selection, not part '
           'of the LinkedIn exports above: a small curated set of standout posts that '
           'helped drive awareness for the community, with their individual metrics. '
           'Refreshed occasionally; newest first.</p>']
    tile_keys = [("impressions", "Impressions"), ("members_reached", "Members reached"),
                 ("video_views", "Video views"), ("article_views", "Article views"),
                 ("engagements", "Engagements")]
    eng_keys = [("reactions", "\U0001F44D", "reactions"), ("comments", "\U0001F4AC", "comments"),
                ("reposts", "\U0001F501", "reposts"), ("saves", "\U0001F516", "saves"),
                ("sends", "\U0001F4E9", "sends")]
    for p in sorted(posts, key=lambda x: x.get("date", ""), reverse=True):
        s = p.get("stats", {})
        plat = p.get("platform", "")
        chip = ('<span class="li-chip"><b>in</b>LinkedIn</span>' if plat.lower() == "linkedin"
                else f'<span class="vid-chip">{esc(plat)}</span>')
        tiles = []
        for k, lbl in tile_keys:
            if k == "article_views" and "video_views" in s:
                continue                       # prefer video_views when both present
            if k in s:
                tiles.append(f'<div class="st"><b>{_num(s[k]):,.0f}</b>'
                             f'<span>{lbl}</span></div>')
        eng = [f'<span>{icon} <b>{_num(s[k]):,.0f}</b> {lbl}</span>'
               for k, icon, lbl in eng_keys if s.get(k)]
        author = p.get("author", "")
        href = esc(safe_url(p.get("url", "")))
        out.append(f'<div class="post"><div class="post-hd">{chip}'
                   f'{f"<span>{esc(author)}</span>" if author else ""}'
                   f'<span class="date">{esc(p.get("date", ""))}</span></div>'
                   f'<a class="post-title" href="{href}" target="_blank" rel="noopener">'
                   f'{esc(p.get("title", ""))}</a>'
                   f'<div class="post-stats">{"".join(tiles)}</div>'
                   + (f'<div class="post-eng">{"".join(eng)}</div>' if eng else "")
                   + '</div>')
    return out


def post_card(p, top_reach, best_rate):
    """One post card. `p` is a dict of the All-posts columns."""
    title = re.sub(r"https?://\S+", "", str(p["title"])).split("\n")[0].strip()
    if len(title) > 200:
        title = title[:197].rstrip() + "…"
    is_video = "video" in str(p["ctype"]).lower()
    chips = ['<span class="li-chip"><b>in</b>LinkedIn</span>']
    if is_video:
        chips.append('<span class="vid-chip">▶ Video</span>')
    if p is top_reach:
        chips.append('<span class="top-chip">Top reach</span>')
    if p is best_rate and best_rate is not top_reach:
        chips.append('<span class="top-chip">Best rate</span>')
    stats = [("impressions", f"{p['impr']:.0f}")]
    if p["views"]:
        stats.append(("views", f"{p['views']:.0f}"))
    stats += [("reactions", f"{p['likes']:.0f}"),
              ("clicks", f"{p['clicks']:.0f}"),
              ("engagement", f"{p['eng'] * 100:.2f}%")]
    st_html = "".join(f'<div class="st"><b>{v}</b><span>{k}</span></div>'
                      for k, v in stats)
    eng = (f'CTR <b>{p["ctr"] * 100:.2f}%</b> · comments '
           f'<b>{p["comments"]:.0f}</b> · reposts <b>{p["reposts"]:.0f}</b>')
    href = esc(safe_url(p["link"])) if p["link"] else "#"
    return (f'  <div class="post">\n'
            f'    <div class="post-hd">{"".join(chips)}'
            f'<span class="date">{esc(p["date"])}</span></div>\n'
            f'    <a class="post-title" href="{href}" target="_blank" '
            f'rel="noopener">{esc(title)}</a>\n'
            f'    <div class="post-stats">{st_html}</div>\n'
            f'    <div class="post-eng">{eng}</div>\n'
            f'  </div>')


CSS = """:root{
  --bg:#0a1020;--panel:rgba(255,255,255,.04);--bd:rgba(255,255,255,.09);
  --tx:#e9eff8;--mut:#9aabc0;--mut2:#6f819a;--ac:#0a66c2;--ac2:#4a9fe8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);
  font:16px/1.6 Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:920px;margin:0 auto;padding:38px 22px 70px}
a{color:var(--ac2)}
h1{font-size:30px;margin:0 0 6px;font-weight:700;letter-spacing:-.02em}
h2{font-size:19px;margin:34px 0 14px;font-weight:700;letter-spacing:-.01em}
h2 .n{color:var(--mut2);font-weight:600;font-size:14px;letter-spacing:0}
.sub{color:var(--mut);margin:0 0 22px;font-size:14.5px}
.tag{display:inline-flex;align-items:center;gap:7px;font-size:11px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ac2);font-weight:700;margin-bottom:6px}
.li-badge{display:inline-flex;align-items:center;background:#0a66c2;color:#fff;
  font-weight:800;font-size:11px;border-radius:3px;padding:1px 4px;letter-spacing:0}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0 6px}
.card{background:var(--panel);border:1px solid var(--bd);border-radius:14px;padding:16px}
.card b{display:block;font-size:27px;font-weight:700;color:var(--ac2);line-height:1.05}
.card b small{font-size:14px;color:var(--mut);font-weight:600}
.card span{font-size:12.5px;color:var(--mut)}
.sec{background:var(--panel);border:1px solid var(--bd);border-radius:16px;padding:20px 22px;margin-bottom:8px}
.sec-hd{font-size:12.5px;font-weight:600;color:var(--tx);margin:0 0 14px}
.sec-hd .mut{color:var(--mut2);font-weight:500}
.drow{margin:13px 0}
.drow:first-of-type{margin-top:2px}
.drow .lab{display:flex;justify-content:space-between;align-items:baseline;gap:10px;font-size:13.5px;margin-bottom:6px}
.drow .lab .l{color:var(--mut);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.drow .lab .v{color:var(--tx);font-weight:700;flex:0 0 auto;font-variant-numeric:tabular-nums}
.drow .track{background:rgba(255,255,255,.05);border-radius:6px;height:8px;overflow:hidden}
.drow .track i{display:block;height:100%;border-radius:6px;background:var(--ac)}
.post{background:var(--panel);border:1px solid var(--bd);border-radius:16px;padding:18px 20px;margin-bottom:12px}
.post-hd{display:flex;align-items:center;gap:10px;margin-bottom:9px;font-size:13px;color:var(--mut)}
.post-hd .date{margin-left:auto;color:var(--mut2);font-size:12.5px}
.li-chip{display:inline-flex;align-items:center;gap:5px;background:#0a66c2;color:#fff;font-size:11px;font-weight:700;padding:3px 8px 3px 6px;border-radius:5px}
.li-chip b{background:#fff;color:#0a66c2;border-radius:2px;padding:0 3px;font-size:10.5px;line-height:1.4}
.vid-chip{background:rgba(255,255,255,.08);color:var(--mut);font-size:11px;font-weight:600;padding:2px 8px;border-radius:5px}
.top-chip{background:rgba(74,159,232,.15);color:var(--ac2);font-size:11px;font-weight:700;padding:2px 8px;border-radius:5px}
.post-title{font-size:16px;font-weight:700;color:var(--tx);text-decoration:none;line-height:1.35;display:inline-block}
.post-title:hover{color:var(--ac2);text-decoration:underline}
.post-stats{display:flex;gap:30px;margin:15px 0 12px;flex-wrap:wrap}
.post-stats .st b{display:block;font-size:20px;font-weight:700;color:var(--ac2);line-height:1.05}
.post-stats .st span{font-size:11.5px;color:var(--mut)}
.post-eng{font-size:13px;color:var(--mut);display:flex;gap:18px;flex-wrap:wrap;border-top:1px solid var(--bd);padding-top:11px}
.post-eng b{color:var(--tx);font-weight:600}
.grid2{columns:2;column-gap:12px}
.grid2 .sec{break-inside:avoid;-webkit-column-break-inside:avoid;margin-bottom:12px}
.foot{color:var(--mut2);font-size:12px;margin-top:30px;border-top:1px solid var(--bd);padding-top:16px}
.warn{border:1px solid #7a5a1d;background:linear-gradient(160deg,rgba(255,193,64,.10),rgba(255,255,255,.01));
  border-radius:12px;padding:12px 16px;margin:14px 0;color:#ffd98a;font-size:13.5px}
.warn code{background:rgba(255,255,255,.07);padding:1px 5px;border-radius:4px;font-size:12.5px}
@media(max-width:680px){
  .cards{grid-template-columns:repeat(2,1fr)}

  .grid2{columns:1}}"""


def build(followers_xls, content_xls, visitors_xls, snapshot):
    fw = xlrd.open_workbook(followers_xls)
    cw = xlrd.open_workbook(content_xls)
    vw = xlrd.open_workbook(visitors_xls)

    # ── followers ────────────────────────────────────────────────────────────
    fnew = series(fw.sheet_by_name("New followers"), 1, 2, 3, 4)  # spon,org,ai,total
    daily_new = [(d, tot) for (d, sp, org, ai, tot) in fnew]
    followers_total = sum(v for _, v in daily_new)
    organic = sum(org for (_, sp, org, ai, tot) in fnew)
    paid = sum(sp + ai for (_, sp, org, ai, tot) in fnew)

    # ── content ──────────────────────────────────────────────────────────────
    met = series(cw.sheet_by_name("Metrics"), 3)  # impressions (total)
    impressions = sum(v for _, v in met)
    ap = cw.sheet_by_name("All posts")
    # The 'All posts' header row starts with 'Post title' (a description line
    # sits above it); default to 0 and tolerate an empty sheet (no posts yet).
    hp = 0
    for r in range(min(4, ap.nrows)):
        if str(_cell(ap, r, 0)).strip().lower() == "post title":
            hp = r
            break
    posts = []
    for r in range(hp + 1, ap.nrows):
        if not str(_cell(ap, r, 0)).strip():
            continue
        posts.append(dict(
            title=_cell(ap, r, 0), link=_cell(ap, r, 1),
            date=_cell(ap, r, 5), impr=_num(_cell(ap, r, 9)),
            views=_num(_cell(ap, r, 10)), clicks=_num(_cell(ap, r, 12)),
            ctr=_num(_cell(ap, r, 13)), likes=_num(_cell(ap, r, 14)),
            comments=_num(_cell(ap, r, 15)), reposts=_num(_cell(ap, r, 16)),
            eng=_num(_cell(ap, r, 18)), ctype=_cell(ap, r, 19)))
    posts.sort(key=lambda p: -p["impr"])
    top_reach = posts[0] if posts else None
    best_rate = max(posts, key=lambda p: p["eng"]) if posts else None

    # ── visitors ─────────────────────────────────────────────────────────────
    vm = vw.sheet_by_name("Visitor metrics")
    vrows = series(vm, 19, 20, 21, 24)  # pv desktop, pv mobile, pv total, uniq total
    pageviews = sum(t for (_, dk, mb, t, u) in vrows)
    uniques = sum(u for (_, dk, mb, t, u) in vrows)
    days_views = [(d, t) for (d, dk, mb, t, u) in vrows]

    # ── window + activity ────────────────────────────────────────────────────
    active = {d for (d, n) in daily_new if n} | {d for (d, v) in met if v} \
        | {d for (d, dk, mb, t, u) in vrows if t}
    days_live = len(active)
    d0 = daily_new[0][0] if daily_new else None
    dN = daily_new[-1][0] if daily_new else None
    win = (f"{d0.strftime('%m/%d')} → {dN.strftime('%m/%d/%Y')}"
           if d0 else "—")

    # ── assemble ─────────────────────────────────────────────────────────────
    P = [f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
         f'<meta name="viewport" content="width=device-width, initial-scale=1">'
         f'<title>LinkedIn Community — Stats</title><style>{CSS}</style></head>'
         f'<body><div class="wrap">']
    P.append('<span class="tag"><span class="li-badge">in</span> LinkedIn · '
             'open-agent-ai-security · manual export</span>')
    P.append('<h1>LinkedIn Community — Stats</h1>')
    P.append(f'<p class="sub">Companion to <a href="./">Community Traffic</a>, '
             f'tracking the <a href="https://www.linkedin.com/company/'
             f'open-agent-and-ai-security-community/">Open Agent &amp; AI Security '
             f'Community</a> LinkedIn page — our standing record of LinkedIn '
             f'audience, content, and visitors over time. Latest export covers '
             f'<b>{win}</b>.</p>')
    P.append('<div class="warn"><b>Not auto-updated</b> — this page is refreshed '
             'periodically from a manual LinkedIn data pull, snapshot '
             f'<b>{snapshot.strftime("%m/%d/%Y")}</b>.</div>')

    org_note = " · all organic" if paid == 0 else ""
    P.append('<div class="cards">')
    P.append(f'<div class="card"><b>{followers_total:,.0f}</b>'
             f'<span>Followers{org_note}</span></div>')
    P.append(f'<div class="card"><b>{impressions:,.0f}</b>'
             f'<span>Post impressions · {len(posts)} post'
             f'{"s" if len(posts) != 1 else ""}</span></div>')
    P.append(f'<div class="card"><b>{pageviews:,.0f} '
             f'<small>/ {uniques:,.0f} uniq</small></b>'
             f'<span>Page views / visitors</span></div>')
    P.append(f'<div class="card"><b>{days_live}</b><span>Active days</span></div>')
    P.append('</div>')

    P.append('<h2>Total followers <span class="n">· cumulative</span></h2>')
    P.append('<div class="sec" style="padding:16px 18px 10px">')
    P.append(f'<div class="sec-hd">Follower count over time '
             f'<span class="mut">— 0 → {followers_total:,.0f}, '
             f'{"all organic" if paid == 0 else "organic + paid"}</span></div>')
    P.append(cumulative_line(daily_new))
    P.append('</div>')

    P.append('<h2>Who\'s following</h2>')
    P.append('<div class="grid2">')
    for sheet, title in [("Seniority", "Seniority"), ("Industry", "Industry"),
                         ("Company size", "Company size"), ("Location", "Locations")]:
        rows = demographic(fw.sheet_by_name(sheet))
        P.append(panel(title, f"{sum(v for _, v in rows):.0f} classified", rows,
                       clean=(sheet == "Location")))
    P.append('</div>')

    P.append('<h2>Posts <span class="n">· organic</span></h2>')
    for p in posts:
        P.append(post_card(p, top_reach, best_rate))

    P.append(f'<h2>Page visitors <span class="n">· {pageviews:,.0f} views / '
             f'{uniques:,.0f} unique</span></h2>')
    views_avg_window = 5
    P.append('<div class="sec" style="padding:16px 18px 10px">')
    P.append(f'<div class="sec-hd">Page views by day '
             f'<span class="mut">— {pageviews:,.0f} views over {days_live} active '
             f'days, {views_avg_window}-day trend</span></div>')
    P.append(views_trend_svg(days_views, avg_window=views_avg_window))
    P.append('</div>')

    P.append('<h2>Who\'s visiting <span class="n">· view-weighted</span></h2>')
    P.append('<p class="sub" style="margin-bottom:10px">Distinct from followers — '
             'visitor demographics count page <b>views</b> (not people), so they read '
             'as share, not headcount.</p>')
    P.append('<div class="grid2">')
    for sheet in ["Seniority", "Company size", "Industry", "Location"]:
        rows = demographic(vw.sheet_by_name(sheet))
        P.append(panel(sheet, f"{sum(v for _, v in rows):.0f} views", rows,
                       clean=(sheet == "Location")))
    P.append('</div>')

    # Featured posts last: a separate source (individual curated post metrics),
    # distinct from the bulk .xls page exports above.
    P.extend(featured_posts_section())

    P.append(f'<div class="foot">Source: LinkedIn analytics exports '
             f'(<b>followers · content · visitors</b>), org page '
             f'<code>open-agent-and-ai-security-community</code>, snapshot '
             f'{snapshot.strftime("%m/%d/%Y")} · window {win}. Demographic breakdowns '
             f'cover only LinkedIn-classifiable members and are view-weighted where '
             f'noted, so treat them as directional. Not auto-updated — refreshed '
             f'periodically from a manual data pull. · open-agent-ai-security</div>')
    P.append('</div></body></html>')
    return "\n".join(P)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exports", default=os.path.join(HERE, "linkedin-exports"),
                    help="directory holding the three *_followers/content/visitors_*.xls")
    ap.add_argument("--out", default=os.path.join(HERE, "linkedin.html"),
                    help="output HTML path")
    a = ap.parse_args()

    files = {k: _newest(a.exports, k) for k in ("followers", "content", "visitors")}
    missing = [k for k, v in files.items() if not v]
    if missing:
        sys.exit(f"missing LinkedIn export(s) in {a.exports}: {', '.join(missing)}\n"
                 "download all three tabs (Followers / Content / Visitors) and drop "
                 "the .xls files there.")
    for k, v in files.items():
        print(f"  {k:<10} {os.path.basename(v)}")

    snapshot = datetime.date.today()
    try:
        out_html = build(files["followers"], files["content"],
                         files["visitors"], snapshot)
    except (xlrd.XLRDError, IndexError, KeyError) as e:
        sys.exit(f"couldn't parse a LinkedIn export ({type(e).__name__}: {e}).\n"
                 "LinkedIn may have changed the export layout (sheet/column names) "
                 "— re-download the three tabs, or check the sheet structure.")
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(out_html)
    print(f"wrote {a.out}  ({len(out_html):,} bytes)")


if __name__ == "__main__":
    main()

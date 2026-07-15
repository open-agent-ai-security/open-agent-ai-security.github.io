#!/usr/bin/env python3
# Copyright 2026 Exabeam, Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Build the cumulative GitHub-stars trend chart (community-stars.svg) from real
`starred_at` timestamps — one smooth line per project. Self-contained, responsive,
theme-aware SVG (CSS vars resolve against the page); generate.py embeds it inline
in the "GitHub stars" section, inside the same translucent panel as every other
chart. No baked-in title/background — the section <h2> supplies the heading.

Replaces the star-history.com dependency (rate-limited). Smooth (monotone-clamped
Catmull-Rom) curves rather than a step staircase, so the trend reads at a glance.

Auth: uses the `gh` CLI (public data, but gh avoids anonymous rate limits).
Run:  python3 stats/make_stars_svg.py
"""
import json, subprocess, datetime, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRIPT_DIR, "community-stars.svg")

# Key dates (shared with the Daily Views chart) → vertical markers on the trend.
KEY_DATES = os.path.join(SCRIPT_DIR, "key-dates.json")
key_dates = {}
if os.path.exists(KEY_DATES):
    with open(KEY_DATES, encoding="utf-8") as _fh:
        key_dates = {k: v for k, v in json.load(_fh).items() if not k.startswith("_")}

# (label, repo, color) — colors match PROJECTS in generate.py
SERIES = [
    ("Praxen",   "open-agent-ai-security/praxen",   "#ff7a2e"),
    ("Observra", "open-agent-ai-security/observra", "#37c2f0"),
]

# Match the report's other line charts (generate.py cumulative_svg/trend_svg):
# 720-wide, ~180 plot, thin marks, theme CSS vars, title from the section <h2>.
W, H = 720, 230
ML, MR, MT, MB = 40, 14, 16, 34
PW, PH = W - ML - MR, H - MT - MB


def stargazer_times(repo):
    """All starred_at timestamps for a repo (paginated), oldest first."""
    out = subprocess.run(
        ["gh", "api", "--paginate", "-H", "Accept: application/vnd.github.star+json",
         f"/repos/{repo}/stargazers?per_page=100"],
        capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"gh api stargazers {repo} failed:\n{out.stderr.strip()}")
    stamps = [datetime.datetime.strptime(s["starred_at"], "%Y-%m-%dT%H:%M:%SZ")
              for s in json.loads(out.stdout)]
    return sorted(stamps)


series, all_dates = [], []
for label, repo, color in SERIES:
    stamps = stargazer_times(repo)
    series.append((label, color, [(stamps[i], i + 1) for i in range(len(stamps))]))
    all_dates += stamps

t0 = min(all_dates)
t1 = datetime.datetime.utcnow()
span = (t1 - t0).total_seconds() or 1
ymax = max((len(p) for _l, _c, p in series), default=5)
ymax = max(5, ((ymax + 4) // 5) * 5)


def x(dt): return ML + (dt - t0).total_seconds() / span * PW
def y(v):  return MT + PH - (v / ymax) * PH


def smooth(pts):
    """Monotone-clamped Catmull-Rom → cubic Béziers. Control points are clamped
    to each segment's box so a cumulative (never-decreasing) series can't dip."""
    if len(pts) < 2:
        return f'M {pts[0][0]:.1f} {pts[0][1]:.1f}' if pts else ''
    d, n = [f'M {pts[0][0]:.1f} {pts[0][1]:.1f}'], len(pts)
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[0]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[n - 1]
        c1x, c1y = p1[0] + (p2[0] - p0[0]) / 6.0, p1[1] + (p2[1] - p0[1]) / 6.0
        c2x, c2y = p2[0] - (p3[0] - p1[0]) / 6.0, p2[1] - (p3[1] - p1[1]) / 6.0
        xlo, xhi = min(p1[0], p2[0]), max(p1[0], p2[0])
        ylo, yhi = min(p1[1], p2[1]), max(p1[1], p2[1])
        c1x, c2x = min(max(c1x, xlo), xhi), min(max(c2x, xlo), xhi)
        c1y, c2y = min(max(c1y, ylo), yhi), min(max(c2y, ylo), yhi)
        d.append(f'C {c1x:.1f} {c1y:.1f} {c2x:.1f} {c2y:.1f} {p2[0]:.1f} {p2[1]:.1f}')
    return ' '.join(d)


# Theme-aware (CSS vars resolve against the page :root when inlined), no baked-in
# title/background — generate.py wraps it in the section <h2> + translucent .sec box.
svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
    f'width="100%" role="img" style="display:block;max-width:100%;height:auto;'
    f'font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif">',
]
for i in range(6):                            # y gridlines + labels
    v = ymax * i / 5
    yy = y(v)
    svg.append(f'<line x1="{ML}" y1="{yy:.1f}" x2="{ML+PW}" y2="{yy:.1f}" '
               f'stroke="var(--bd)" stroke-width="1" '
               f'opacity="{0.85 if i == 0 else 0.33}"/>')
    svg.append(f'<text x="{ML-7}" y="{yy+3:.1f}" font-size="9" fill="var(--mut2)" '
               f'text-anchor="end">{v:.0f}</text>')
for i in range(6):                            # x date ticks
    dt = t0 + datetime.timedelta(seconds=span * i / 5)
    xx = x(dt)
    svg.append(f'<line x1="{xx:.1f}" y1="{MT+PH}" x2="{xx:.1f}" y2="{MT+PH+4}" '
               f'stroke="var(--bd)" stroke-width="1"/>')
    svg.append(f'<text x="{xx:.1f}" y="{MT+PH+18:.1f}" font-size="10" fill="var(--mut)" '
               f'text-anchor="middle">{dt.strftime("%b %d")}</text>')
for label, color, pts in series:              # smooth series lines
    if not pts:
        continue
    ppts = [(x(t0), y(0))] + [(x(dt), y(v)) for dt, v in pts] \
        + [(x(t1), y(pts[-1][1]))]
    svg.append(f'<path d="{smooth(ppts)}" fill="none" stroke="{color}" '
               f'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>')
    svg.append(f'<circle cx="{x(t1):.1f}" cy="{y(pts[-1][1]):.1f}" r="3.6" '
               f'fill="{color}"/>')
for ds, lbl in sorted(key_dates.items()):      # key-date markers (on top of curves)
    try:
        kdt = datetime.datetime.strptime(ds, "%Y-%m-%d")
    except ValueError:
        continue
    if not (t0 <= kdt <= t1):
        continue
    kx = x(kdt)
    svg.append(f'<line x1="{kx:.1f}" y1="{MT}" x2="{kx:.1f}" y2="{MT+PH}" '
               f'stroke="#e0a52e" stroke-width="1" stroke-dasharray="2 3" '
               f'opacity="0.5"/>')
    svg.append(f'<text x="{kx-4:.1f}" y="{MT+PH-8:.1f}" '
               f'transform="rotate(-90 {kx-4:.1f} {MT+PH-8:.1f})" text-anchor="start" '
               f'font-size="9.5" font-weight="600" fill="#e0a52e">'
               f'&#9670; {lbl}</text>')

lx, ly = ML + 12, MT + 16                       # legend
for i, (label, color, pts) in enumerate(series):
    yy = ly + i * 20
    svg.append(f'<rect x="{lx}" y="{yy-9}" width="12" height="12" rx="3" fill="{color}"/>')
    svg.append(f'<text x="{lx+18}" y="{yy+1}" font-size="12" font-weight="600" '
               f'fill="var(--tx)">{label} &#183; {len(pts)}&#9733;</text>')
svg.append('</svg>')

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("".join(svg))
print(f"Wrote {OUT}  ({os.path.getsize(OUT)} bytes)")
for label, color, pts in series:
    print(f"  {label:<10} {len(pts)} stars")

#!/usr/bin/env python3
# Copyright 2026 Exabeam, Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Community mini-blog generator — Open Agent and AI Security Community.

Builds blog/index.html (chronological post list) and one blog/<slug>/index.html
per post from Markdown sources in blog/posts/. Same "generate and commit" model
as stats/generate.py and stats/make_linkedin.py: self-contained output, no
client-side JS, regenerate locally and commit the result.

Post format — blog/posts/YYYY-MM-DD-slug.md, a --- delimited frontmatter block
(plain `key: value` lines, no YAML) followed by a Markdown body:

  ---
  title: Observra 1.1: Any Agent, No Adapter Required
  author: Steve Wilson
  date: 2026-08-04
  summary: One-line teaser shown on the index card and in link previews.
  tags: release, observra
  ---

  Body starts here, plain Markdown.

Required frontmatter fields: title, author, date. The filename's YYYY-MM-DD-
prefix is stripped to make the slug (and the URL); everything else (nav order,
routing) is derived from that — there's no hand-curated page list like
observra/praxen's docs_build.py PAGES, because a blog's order is inherent
(newest first), not an editorial choice.

Markdown -> HTML via the `markdown` library (tables, fenced_code, toc,
sane_lists) — the same dependency and extension set observra/praxen already
pin in requirements-dev.txt for their own docs_build.py, so this isn't a new
dependency precedent for the org. The on-page table of contents mirrors those
repos' onpage_toc() helper: a thin wrapper around the toc extension's own
token tree (H2 headings only), not a hand-rolled heading walker.

Regenerate:
  pip install -r requirements-dev.txt
  python3 blog/generate_blog.py
"""
import os, re, sys, html, glob, datetime
import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(HERE, "posts")
SITE = "https://open-agent-ai-security.github.io"

REQUIRED = ("title", "author", "date")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")

esc = lambda s: html.escape(str(s), quote=True)


def parse_post(path):
    text = open(path, encoding="utf-8").read()
    m = FRONTMATTER_RE.match(text)
    if not m:
        sys.exit(f"{path}: missing --- frontmatter block")
    raw_meta, body = m.groups()

    meta = {}
    for line in raw_meta.splitlines():
        if not line.strip() or ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()

    missing = [f for f in REQUIRED if not meta.get(f)]
    if missing:
        sys.exit(f"{path}: missing required frontmatter field(s): {', '.join(missing)}")
    try:
        datetime.datetime.strptime(meta["date"], "%Y-%m-%d")
    except ValueError:
        sys.exit(f"{path}: date must be YYYY-MM-DD, got {meta['date']!r}")

    meta["slug"] = DATE_PREFIX_RE.sub("", os.path.splitext(os.path.basename(path))[0])
    meta["tags"] = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]

    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"])
    meta["body_html"] = md.convert(body.strip())
    meta["toc_html"] = onpage_toc(md.toc_tokens)
    return meta


def onpage_toc(toc_tokens):
    """Flat H2-only on-page TOC — mirrors observra/praxen's docs_build.py
    onpage_toc(): a thin wrapper around the toc extension's own token tree,
    not a from-scratch heading walker."""
    items = []

    def walk(tokens):
        for t in tokens:
            if t["level"] == 2:
                items.append(f'<li><a href="#{t["id"]}">{esc(t["name"])}</a></li>')
            walk(t.get("children") or [])

    walk(toc_tokens)
    return f'<ul class="toc">{"".join(items)}</ul>' if items else ""


def strip_tags(html_str):
    return re.sub(r"<[^>]+>", " ", html_str).strip()


def human_date(iso_date):
    return datetime.datetime.strptime(iso_date, "%Y-%m-%d").strftime("%B %d, %Y")


# ── Theme — the flagship site's own tokens (index.html :root, violet accent),
# not the stats dashboard's blue theme, so the blog reads as part of the
# community site rather than a docs subsite. ────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root{--bg:#0b0a18;--panel:rgba(255,255,255,.035);--bd:rgba(255,255,255,.09);--tx:#e9ecf8;--mut:#a0a6c0;--mut2:#757b9a;--ac:#8366f5;--ac2:#8389ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:17px/1.65 Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:44px 22px 80px}
a{color:var(--ac2)}
.brand{display:inline-flex;align-items:center;gap:8px;color:var(--mut);text-decoration:none;font-size:14px;margin-bottom:28px}
.brand:hover{color:var(--tx)}
h1{font-family:"Space Grotesk",Inter,sans-serif;font-size:34px;line-height:1.2;margin:0 0 10px;letter-spacing:-.01em}
h2{font-family:"Space Grotesk",Inter,sans-serif;font-size:22px;margin:34px 0 12px;letter-spacing:-.01em}
h3{font-size:18px;margin:26px 0 10px}
.meta{color:var(--mut);font-size:14px;margin:0 0 30px}
.meta .tag{display:inline-block;background:var(--panel);border:1px solid var(--bd);border-radius:20px;padding:2px 10px;font-size:12px;margin-right:6px}
p{margin:0 0 16px}
code{background:var(--panel);border:1px solid var(--bd);border-radius:4px;padding:1px 5px;font-size:.9em;font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
pre{background:var(--panel);border:1px solid var(--bd);border-radius:10px;padding:14px 16px;overflow-x:auto}
pre code{background:none;border:0;padding:0}
blockquote{margin:0 0 16px;padding:2px 18px;border-left:3px solid var(--ac);color:var(--mut);background:var(--panel);border-radius:0 8px 8px 0}
table{width:100%;border-collapse:collapse;font-size:14.5px;margin:0 0 18px}
th,td{padding:8px 10px;border-bottom:1px solid var(--bd);text-align:left}
th{color:var(--mut);font-weight:600}
ul.toc{list-style:none;margin:0 0 26px;padding:14px 18px;background:var(--panel);border:1px solid var(--bd);border-radius:12px;font-size:13.5px}
ul.toc li{margin:4px 0}
ul.toc a{color:var(--mut)}
ul.toc a:hover{color:var(--ac2)}
.posts{display:flex;flex-direction:column;gap:14px}
.post-card{display:block;background:var(--panel);border:1px solid var(--bd);border-radius:14px;padding:20px 22px;text-decoration:none;transition:border-color .15s}
.post-card:hover{border-color:var(--ac2)}
.post-card .date{color:var(--mut2);font-size:12.5px}
.post-card h2{color:var(--tx);font-size:19px;margin:6px 0 8px}
.post-card p{color:var(--mut);font-size:14.5px;margin:0}
.foot{color:var(--mut2);font-size:12.5px;margin-top:40px;border-top:1px solid var(--bd);padding-top:18px}
@media(max-width:600px){h1{font-size:27px}}
"""


def page_shell(title, description, canonical, body_html, back_href, back_label):
    return (
        f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{esc(title)}</title>'
        f'<meta name="description" content="{esc(description)}">'
        f'<meta name="robots" content="index, follow">'
        f'<link rel="canonical" href="{esc(canonical)}">'
        f'<meta property="og:type" content="article">'
        f'<meta property="og:title" content="{esc(title)}">'
        f'<meta property="og:description" content="{esc(description)}">'
        f'<meta property="og:url" content="{esc(canonical)}">'
        f'<style>{CSS}</style></head><body><div class="wrap">'
        f'<a class="brand" href="{esc(back_href)}">&larr; {esc(back_label)}</a>'
        f'{body_html}'
        f'<div class="foot">Open Agent and AI Security Community</div>'
        f'</div></body></html>'
    )


def render_post_body(meta):
    tags_html = "".join(f'<span class="tag">{esc(t)}</span>' for t in meta["tags"])
    return (
        f'<h1>{esc(meta["title"])}</h1>'
        f'<div class="meta">{human_date(meta["date"])} &middot; {esc(meta["author"])}'
        + (f' &middot; {tags_html}' if tags_html else '')
        + '</div>'
        + meta["toc_html"]
        + meta["body_html"]
    )


def render_index_body(posts):
    cards = []
    for p in posts:
        summary = p.get("summary") or strip_tags(p["body_html"])[:160]
        cards.append(
            f'<a class="post-card" href="{esc(p["slug"])}/">'
            f'<div class="date">{human_date(p["date"])}</div>'
            f'<h2>{esc(p["title"])}</h2>'
            f'<p>{esc(summary)}</p></a>'
        )
    return (
        '<h1>Blog</h1>'
        '<p class="meta">Announcements, release notes, and project updates from the '
        'Open Agent and AI Security Community.</p>'
        f'<div class="posts">{"".join(cards)}</div>'
    )


def main():
    paths = sorted(glob.glob(os.path.join(POSTS_DIR, "*.md")))
    if not paths:
        sys.exit(f"no posts found in {POSTS_DIR}")

    posts = [parse_post(p) for p in paths]
    posts.sort(key=lambda p: p["date"], reverse=True)

    for p in posts:
        out_dir = os.path.join(HERE, p["slug"])
        os.makedirs(out_dir, exist_ok=True)
        description = p.get("summary") or strip_tags(p["body_html"])[:160]
        out_html = page_shell(
            title=f'{p["title"]} — Community Blog',
            description=description,
            canonical=f'{SITE}/blog/{p["slug"]}/',
            body_html=render_post_body(p),
            back_href="../",
            back_label="Blog",
        )
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(out_html)

    index_html = page_shell(
        title="Blog — Open Agent and AI Security Community",
        description="Announcements, release notes, and project updates from the "
                     "Open Agent and AI Security Community.",
        canonical=f"{SITE}/blog/",
        body_html=render_index_body(posts),
        back_href="../",
        back_label="Open Agent & AI Security Community",
    )
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index_html)

    print(f"Wrote {len(posts)} post(s) + blog/index.html")


if __name__ == "__main__":
    main()

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
(plain `key: value` lines, no YAML — though wrapping a value in matching
quotes is tolerated and stripped, since that's an easy habit to fall into)
followed by a Markdown body:

  ---
  title: Observra 1.1: Any Agent, No Adapter Required
  author: Steve Wilson
  date: 2026-08-04
  updated: 2026-08-06
  published: yes
  summary: One-line teaser shown on the index card and in link previews.
  tags: release, observra
  image: observra-1.1.jpg
  image_alt: Optional alt text; defaults to the post title if omitted.
  ---

  Body starts here, plain Markdown.

Required frontmatter fields: title, author, date. The filename's YYYY-MM-DD-
prefix is stripped to make the slug (and the URL); everything else (nav order,
routing) is derived from that — there's no hand-curated page list like
observra/praxen's docs_build.py PAGES, because a blog's order is inherent
(newest first), not an editorial choice.

`updated` is optional (YYYY-MM-DD). Only set it when a post is materially
edited after publishing — it feeds `dateModified` in the JSON-LD, the
sitemap's `<lastmod>`, and a visible "Updated ..." next to the publish date
(omitted entirely when absent or equal to `date`, so most posts never touch
this field).

`published` gates whether a post is publicly discoverable — defaults to NOT
published if omitted (`yes`/`true`/`on`/`1` turn it on, case-insensitive;
anything else, including leaving it out, is a draft). A draft still gets its
own `blog/<slug>/index.html` — written, reviewable, shareable by direct link
for QA — but is left out of the index, both feeds, the sitemap, the blog-wide
JSON-LD, and every other post's "Related posts" pool, and its own page is
`noindex`. Flip it to `yes` and regenerate when it's time to actually launch;
nothing else about the post needs to change. See "Draft workflow" below.

`image` is optional. Either a filename in blog/images/ (checked into git) or a
full http(s) URL. When present it renders as a header banner on the post page
and a thumbnail on the index card; when absent, both layouts fall back to a
text-only rendering — no post is required to have one.

Markdown -> HTML via the `markdown` library (tables, fenced_code, toc,
sane_lists) — the same dependency and extension set observra/praxen already
pin in requirements-dev.txt for their own docs_build.py, so this isn't a new
dependency precedent for the org. The on-page table of contents mirrors those
repos' onpage_toc() helper: a thin wrapper around the toc extension's own
token tree (H2 headings only), not a hand-rolled heading walker.

The page chrome (header nav, footer, sponsor band) is lifted straight from the
root index.html's own markup/CSS — same classes, same asset files, just with
relative paths rewritten for the extra directory depth — so a blog page reads
as the same site, not a themed subsite.

Each post page also gets: an estimated reading time (word count / 200wpm),
a share row (X, LinkedIn, copy-link — plain hrefs plus one small first-party
clipboard script, no third-party embeds), and a "Related posts" block for
any other post sharing at least one tag.

Regenerate:
  pip install -r requirements-dev.txt
  python3 blog/generate_blog.py
"""
import os, re, sys, html, glob, json, datetime, urllib.parse
import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(HERE, "posts")
IMAGES_DIR = os.path.join(HERE, "images")
SITE = "https://open-agent-ai-security.github.io"

# Fallback link-preview image for pages with no post `image` (including the
# index) — same asset the root index.html uses, so a shared blog link always
# gets a real preview instead of a bare title card. Verified 1200x630 (checked
# with Pillow at authoring time; not re-verified at build time since this file
# doesn't change).
DEFAULT_OG_IMAGE = f"{SITE}/assets/community-social.png"
DEFAULT_OG_IMAGE_DIMS = (1200, 630)

REQUIRED = ("title", "author", "date")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")

esc = lambda s: html.escape(str(s), quote=True)


def _truthy(v):
    return str(v).strip().lower() in ("yes", "true", "on", "1")


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
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]  # tolerate YAML-style quoting even though this isn't YAML
        meta[k.strip()] = v

    missing = [f for f in REQUIRED if not meta.get(f)]
    if missing:
        sys.exit(f"{path}: missing required frontmatter field(s): {', '.join(missing)}")
    try:
        datetime.datetime.strptime(meta["date"], "%Y-%m-%d")
    except ValueError:
        sys.exit(f"{path}: date must be YYYY-MM-DD, got {meta['date']!r}")

    meta["updated"] = meta.get("updated", "").strip()
    if meta["updated"]:
        try:
            datetime.datetime.strptime(meta["updated"], "%Y-%m-%d")
        except ValueError:
            sys.exit(f"{path}: updated must be YYYY-MM-DD, got {meta['updated']!r}")

    meta["slug"] = DATE_PREFIX_RE.sub("", os.path.splitext(os.path.basename(path))[0])
    meta["published"] = _truthy(meta.get("published", ""))
    meta["tags"] = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    meta["image"] = meta.get("image", "").strip()
    meta["image_alt"] = meta.get("image_alt", "").strip() or meta["title"]

    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"])
    meta["body_html"] = md.convert(body.strip())
    meta["toc_html"] = onpage_toc(md.toc_tokens)
    meta["reading_time"] = max(1, round(len(strip_tags(meta["body_html"]).split()) / 200))
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


def rfc822_date(iso_date):
    return datetime.datetime.strptime(iso_date, "%Y-%m-%d").strftime("%a, %d %b %Y 00:00:00 GMT")


IMAGE_URL_RE = re.compile(r"^https?://")


def image_url(image, rel):
    """Resolve a frontmatter `image` value against blog/images/, or pass an
    http(s) URL through unchanged. `rel` is the relative path from the page
    being rendered back to the blog/ directory (e.g. "../" from a post page,
    "" from the index itself)."""
    if not image:
        return ""
    return image if IMAGE_URL_RE.match(image) else f"{rel}images/{image}"


BODY_IMG_SRC_RE = re.compile(r'(<img\s[^>]*\bsrc=")([^"]+)(")')


def resolve_body_images(body_html, rel):
    """Rewrite inline post-body images the same way as the `image` frontmatter
    field: a plain Markdown `![alt](filename.png)` with a bare filename (no
    scheme, no leading path) resolves against blog/images/ — one mental model
    for every image in a post, not two. A path already written as absolute,
    explicitly relative (./ or ../), or a full http(s) URL is left untouched,
    so an author can still opt out of the convention when they need to."""
    def resolve(m):
        src = m.group(2)
        if IMAGE_URL_RE.match(src) or src.startswith(("/", "./", "../")):
            return m.group(0)
        return f"{m.group(1)}{rel}images/{src}{m.group(3)}"
    return BODY_IMG_SRC_RE.sub(resolve, body_html)


def local_image_dimensions(image):
    """Best-effort (width, height) for a post's `image` when it's a local
    file in blog/images/ (PNG/JPEG only, read from the header — no Pillow
    dependency for this). Returns None for external http(s) URLs, other
    formats, or anything unreadable: og:image:width/height are then simply
    omitted, and Twitter/LinkedIn size the image themselves on fetch — an
    accurate-but-absent dimension beats a wrong hardcoded one."""
    if not image or IMAGE_URL_RE.match(image):
        return None
    path = os.path.join(IMAGES_DIR, image)
    try:
        with open(path, "rb") as fh:
            head = fh.read(33)
            if head[:8] == b"\x89PNG\r\n\x1a\n" and len(head) >= 33:
                return (int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big"))
            if head[:2] == b"\xff\xd8":
                return _jpeg_dimensions(fh)
    except OSError:
        pass
    return None


def _jpeg_dimensions(fh):
    fh.seek(2)  # past the SOI marker already consumed by the caller's read()
    while True:
        marker = fh.read(2)
        if len(marker) < 2 or marker[0] != 0xFF:
            return None
        code = marker[1]
        if code in (0xD8, 0x01) or 0xD0 <= code <= 0xD7:
            continue
        length = int.from_bytes(fh.read(2), "big")
        if code in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            data = fh.read(5)
            if len(data) < 5:
                return None
            return (int.from_bytes(data[3:5], "big"), int.from_bytes(data[1:3], "big"))
        fh.seek(length - 2, 1)


def analytics_scripts(home):
    """Identical to root index.html's tracking snippet (see that file's own
    comment) — same two cookieless tools, same account/token, just with the
    asset path adjusted for depth. Keep in sync with index.html by hand if
    that snippet ever changes; nothing here reads it automatically."""
    return (
        f'<script data-goatcounter="https://open-agent-ai-security.goatcounter.com/count" '
        f'async src="{esc(home)}assets/count.js"></script>'
        f'<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
        f'data-cf-beacon=\'{{"token": "223642421cad463daf91bd9429a5f9a0"}}\'></script>'
    )


def json_ld_post(meta, canonical, og_image):
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": meta["title"],
        "description": meta.get("summary") or strip_tags(meta["body_html"])[:160],
        "datePublished": meta["date"],
        "author": {"@type": "Person", "name": meta["author"]},
        "publisher": {
            "@type": "Organization",
            "name": "Open Agent and AI Security Community",
            "url": SITE + "/",
            "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/community-social.png"},
        },
        "url": canonical,
        "mainEntityOfPage": canonical,
    }
    if meta["updated"] and meta["updated"] != meta["date"]:
        data["dateModified"] = meta["updated"]
    if og_image:
        data["image"] = og_image
    if meta["tags"]:
        data["keywords"] = ", ".join(meta["tags"])
    return json.dumps(data, ensure_ascii=False)


def json_ld_index(posts):
    data = {
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": "Blog — Open Agent and AI Security Community",
        "url": f"{SITE}/blog/",
        "blogPost": [
            {
                "@type": "BlogPosting",
                "headline": p["title"],
                "url": f'{SITE}/blog/{p["slug"]}/',
                "datePublished": p["date"],
                **({"dateModified": p["updated"]} if p["updated"] and p["updated"] != p["date"] else {}),
                "author": {"@type": "Person", "name": p["author"]},
            }
            for p in posts
        ],
    }
    return json.dumps(data, ensure_ascii=False)


GITHUB_ICON = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
    '<path d="M12 .5C5.7.5.5 5.7.5 12c0 5.1 3.3 9.4 7.9 10.9.6.1.8-.2.8-.6v-2c-3.2.7-3.9-1.4-3.9-1.4-.5-1.3-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 '
    '1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 '
    '3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.7 18.3 5 18.3 5c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 '
    '.4.2.7.8.6 4.6-1.5 7.9-5.8 7.9-10.9C23.5 5.7 18.3.5 12 .5z"/></svg>'
)

X_ICON = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
    '<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 '
    '17.52h1.833L7.084 4.126H5.117z"/></svg>'
)

LINKEDIN_ICON = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
    '<path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 '
    '1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 '
    '1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 '
    '1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>'
)

COPY_LINK_JS = (
    "<script>document.addEventListener('click',function(e){"
    "var b=e.target.closest('.copy-link');if(!b)return;"
    "navigator.clipboard.writeText(b.getAttribute('data-url')).then(function(){"
    "var t=b.textContent;b.textContent='Copied!';"
    "setTimeout(function(){b.textContent=t;},1500);});});</script>"
)


# ── Theme — the landing page's own tokens, header/footer markup, and CSS
# classes (index.html :root + header.nav + footer), reused verbatim with
# relative paths adjusted for depth, so a blog page is visibly the same site
# rather than a flat, differently-themed subsite. ───────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root{--bg:#0b0a18;--bg2:#0e0d20;--panel:rgba(255,255,255,.035);--panel2:rgba(255,255,255,.05);--bd:rgba(255,255,255,.09);--bd-hi:rgba(131,102,245,.45);--tx:#e9ecf8;--mut:#a0a6c0;--mut2:#757b9a;--violet:#8366f5;--violet-deep:#8300d8;--violet-2:#837ffc;--violet-lite:#8389ff;--ac:#8366f5;--ac2:#8389ff;--maxw:1140px}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--tx);font:17px/1.65 Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
img{max-width:100%;display:block}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 24px}
a{color:var(--violet-2);text-decoration:none}
a:hover{color:var(--violet-lite)}
.grad{background:linear-gradient(100deg,var(--violet-lite),var(--violet) 55%,var(--violet-deep));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:transparent}
.eyebrow{text-transform:uppercase;letter-spacing:.18em;font-size:12.5px;font-weight:600;color:var(--violet-2);margin:0 0 14px}

/* ---------- Nav (identical to root index.html) ---------- */
header.nav{position:sticky;top:0;z-index:50;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);background:rgba(11,10,24,.72);border-bottom:1px solid var(--bd)}
.nav-inner{display:flex;align-items:center;justify-content:space-between;gap:20px;height:66px}
.brand{display:inline-flex;align-items:center}
.brand img.logo{height:30px;width:auto;display:block}
.nav-links{display:flex;align-items:center;gap:26px}
.nav-links a{color:var(--mut);font-weight:500;font-size:14.5px}
.nav-links a:hover{color:var(--tx)}
.nav-links a.active{color:var(--violet-2)}
.btn{display:inline-flex;align-items:center;gap:8px;cursor:pointer;font-weight:600;font-size:15px;border-radius:11px;padding:11px 20px;border:1px solid transparent;transition:all .18s ease;font-family:inherit;text-decoration:none}
.btn-ghost{color:var(--tx);border-color:var(--bd);background:var(--panel)}
.btn-ghost:hover{border-color:var(--bd-hi);background:var(--panel2);color:var(--tx)}
.nav-cta .btn{padding:9px 16px;font-size:14px}
@media(max-width:680px){.nav-links{display:none}}

/* ---------- Ambient glow behind the content column (toned-down hero) ----- */
main{position:relative}
main::before{content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;
  background:radial-gradient(720px 460px at 78% 0%,rgba(131,102,245,.16),transparent 60%),
             radial-gradient(620px 420px at 6% 40%,rgba(131,0,216,.10),transparent 60%);}

/* ---------- Content column ---------- */
.content{max-width:740px;margin:0 auto;padding:52px 24px 84px}
h1{font-family:"Space Grotesk",Inter,sans-serif;font-size:36px;line-height:1.18;margin:0 0 12px;letter-spacing:-.01em;font-weight:700}
h2{font-family:"Space Grotesk",Inter,sans-serif;font-size:22px;margin:34px 0 12px;letter-spacing:-.01em;font-weight:600}
h3{font-size:18px;margin:26px 0 10px}
.meta{color:var(--mut);font-size:14px;margin:0 0 30px}
.meta .tag{display:inline-block;background:var(--panel);border:1px solid var(--bd);border-radius:20px;padding:2px 10px;font-size:11.5px;letter-spacing:.04em;text-transform:uppercase;color:var(--violet-2);font-weight:600;margin-right:6px}
.content p{margin:0 0 16px;color:var(--tx)}
code{background:var(--panel);border:1px solid var(--bd);border-radius:4px;padding:1px 5px;font-size:.9em;font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
pre{background:var(--panel);border:1px solid var(--bd);border-radius:10px;padding:14px 16px;overflow-x:auto}
pre code{background:none;border:0;padding:0}
blockquote{margin:0 0 16px;padding:2px 18px;border-left:3px solid var(--violet);color:var(--mut);background:var(--panel);border-radius:0 8px 8px 0}
table{width:100%;border-collapse:collapse;font-size:14.5px;margin:0 0 18px}
th,td{padding:8px 10px;border-bottom:1px solid var(--bd);text-align:left}
th{color:var(--mut);font-weight:600}
ul.toc{list-style:none;margin:0 0 26px;padding:14px 18px;background:var(--panel);border:1px solid var(--bd);border-radius:12px;font-size:13.5px}
ul.toc li{margin:4px 0}
ul.toc a{color:var(--mut)}
ul.toc a:hover{color:var(--violet-2)}
.draft-banner{border:1px solid #7a5a1d;background:linear-gradient(160deg,rgba(255,193,64,.12),rgba(255,255,255,.01));border-radius:12px;padding:12px 16px;margin:0 0 24px;color:#ffd98a;font-size:13.5px}
.draft-banner code{background:rgba(255,193,64,.14);border-color:#7a5a1d;color:#ffd98a}
.post-hero{width:100%;aspect-ratio:2/1;object-fit:cover;border-radius:16px;border:1px solid var(--bd);margin:0 0 26px;background:var(--panel)}
.content p img{border-radius:12px;border:1px solid var(--bd);background:var(--panel);margin:6px 0 20px}
.share{display:flex;align-items:center;gap:10px;margin-top:40px;padding-top:26px;border-top:1px solid var(--bd)}
.share-label{color:var(--mut2);font-size:12px;text-transform:uppercase;letter-spacing:.12em;margin-right:2px}
.share-btn{display:inline-flex;align-items:center;gap:6px;background:var(--panel);border:1px solid var(--bd);border-radius:8px;padding:7px 12px;color:var(--mut);font-size:12.5px;font-family:inherit;line-height:1;cursor:pointer;transition:border-color .15s,color .15s}
.share-btn:hover{border-color:var(--bd-hi);color:var(--tx)}
.related{margin-top:34px}
.related h2{margin-top:0}
.related-list{display:flex;gap:14px;flex-wrap:wrap}
.related-card{flex:1 1 200px;background:var(--panel);border:1px solid var(--bd);border-radius:12px;padding:16px 18px;text-decoration:none;transition:border-color .15s,background .15s}
.related-card:hover{border-color:var(--bd-hi);background:var(--panel2)}
.related-card .date{color:var(--mut2);font-size:12px}
.related-card h3{color:var(--tx);font-size:15.5px;margin:6px 0 0;font-weight:600}
.hero-card{display:block;text-decoration:none;margin:22px 0 40px;padding:22px 24px 26px;background:var(--panel);border:1px solid var(--bd);border-radius:20px;transition:border-color .15s,background .15s}
.hero-card:hover{border-color:var(--bd-hi);background:var(--panel2)}
.hero-thumb{width:100%;aspect-ratio:2/1;object-fit:cover;border-radius:14px;border:1px solid var(--bd);background:var(--bg2);margin:0 0 20px}
.hero-card h2{color:var(--tx);font-family:"Space Grotesk",Inter,sans-serif;font-size:30px;line-height:1.2;font-weight:700;letter-spacing:-.01em;margin:0 0 8px}
.hero-card .date{color:var(--mut2);font-size:13px;margin:0 0 12px}
.hero-card p{color:var(--mut);font-size:16px;line-height:1.6;margin:0;max-width:640px}
.more-label{font-family:"Space Grotesk",Inter,sans-serif;font-size:15px;font-weight:600;color:var(--mut);text-transform:uppercase;letter-spacing:.08em;margin:0 0 16px;padding-top:6px;border-top:1px solid var(--bd)}
.posts{display:flex;flex-direction:column;gap:14px}
.post-card{display:flex;gap:18px;align-items:flex-start;background:var(--panel);border:1px solid var(--bd);border-radius:14px;padding:16px;text-decoration:none;transition:border-color .15s,background .15s}
.post-card:hover{border-color:var(--bd-hi);background:var(--panel2)}
.post-thumb{flex:0 0 200px;width:200px;aspect-ratio:2/1;height:auto;border-radius:10px;object-fit:cover;background:var(--bg2)}
.post-body{flex:1 1 auto;min-width:0;padding:4px 6px}
.post-card .date{color:var(--mut2);font-size:12.5px}
.post-card h2{color:var(--tx);font-size:19px;margin:6px 0 8px}
.post-card p{color:var(--mut);font-size:14.5px;margin:0}
@media(max-width:560px){.post-card{flex-direction:column}.post-thumb{width:100%;flex-basis:auto}.hero-card h2{font-size:24px}}

/* ---------- Footer (identical to root index.html) ---------- */
footer{border-top:1px solid var(--bd);background:var(--bg2);padding:50px 0 38px}
.foot-grid{display:flex;justify-content:space-between;gap:40px;flex-wrap:wrap;align-items:flex-start}
.foot-brand{max-width:360px}
.foot-brand img{height:40px;width:auto;margin-bottom:16px}
.foot-brand p{color:var(--mut);font-size:14.5px;margin:0}
.foot-col h4{font-size:13px;text-transform:uppercase;letter-spacing:.12em;color:var(--mut2);margin:0 0 14px}
.foot-col a{display:block;color:var(--mut);font-size:14.5px;margin-bottom:10px}
.foot-col a:hover{color:var(--tx)}
.foot-bottom{display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;margin-top:34px;padding-top:26px;border-top:1px solid var(--bd);color:var(--mut2);font-size:13.5px}
.sponsor-band{position:relative;overflow:hidden;margin-top:44px;padding:34px 30px;border:1px solid var(--bd);border-radius:18px;background:linear-gradient(180deg,rgba(255,255,255,.035),rgba(255,255,255,.012));display:flex;flex-direction:column;align-items:center;gap:16px;text-align:center}
.sponsor-band::before{content:"";position:absolute;inset:0;z-index:0;pointer-events:none;background:radial-gradient(460px 130px at 50% 118%,rgba(131,102,245,.18),transparent 70%),radial-gradient(460px 130px at 50% -18%,rgba(131,0,216,.14),transparent 70%)}
.sponsor-band>*{position:relative;z-index:1}
.sponsor-band .lbl{font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--mut2);font-weight:600}
.sponsor-band a.exa{display:inline-block;padding:4px 6px;line-height:0}
.exa-logo{height:32px;width:auto;display:block;opacity:.96;transition:opacity .2s ease}
.sponsor-band a.exa:hover .exa-logo{opacity:1}
.sponsor-note{max-width:540px;margin:2px 0 0;color:var(--mut);font-size:14.5px;line-height:1.6}
@media(max-width:600px){h1{font-size:28px}.foot-grid{gap:30px}}
"""


def site_header(home, blog_home, active_blog):
    """home = relative path to the site root; blog_home = relative path to the
    blog index. Reuses the exact header markup/classes from root index.html."""
    active = ' class="active"' if active_blog else ""
    return (
        f'<header class="nav"><div class="wrap nav-inner">'
        f'<a class="brand" href="{esc(home)}">'
        f'<img class="logo" src="{esc(home)}assets/community-logo-dark-background.svg" '
        f'alt="Open Agent &amp; AI Security Community" width="131" height="30"></a>'
        f'<nav class="nav-links">'
        f'<a href="{esc(home)}#mission">Mission &amp; vision</a>'
        f'<a href="{esc(home)}#purpose">Purpose</a>'
        f'<a href="{esc(home)}#projects">Projects</a>'
        f'<a href="{esc(blog_home)}"{active}>Blog</a>'
        f'<a href="{esc(home)}#join">Join</a>'
        f'</nav>'
        f'<div class="nav-cta"><a class="btn btn-ghost" '
        f'href="https://github.com/open-agent-ai-security" target="_blank" rel="noopener">'
        f'{GITHUB_ICON} GitHub</a></div>'
        f'</div></header>'
    )


def site_footer(home):
    """Reuses the exact footer markup/classes from root index.html."""
    return (
        '<footer><div class="wrap">'
        '<div class="foot-grid">'
        '<div class="foot-brand">'
        f'<img src="{esc(home)}assets/community-logo-dark-background.svg" '
        'alt="Open Agent and AI Security Community logo">'
        '<p>An open, collaborative community securing agentic enterprise applications '
        'and advancing the responsible use of AI in security operations.</p>'
        '</div>'
        '<div class="foot-col"><h4>Projects</h4>'
        '<a href="https://open-agent-ai-security.github.io/praxen/">Praxen</a>'
        '<a href="https://open-agent-ai-security.github.io/observra/">Observra</a>'
        '</div>'
        '<div class="foot-col"><h4>Community</h4>'
        f'<a href="{esc(home)}#join">Get involved</a>'
        '<a href="https://www.linkedin.com/company/open-agent-and-ai-security-community/" '
        'target="_blank" rel="noopener">LinkedIn</a>'
        f'<a href="{esc(home)}#mission">Mission &amp; vision</a>'
        '</div>'
        '</div>'
        '<div class="sponsor-band"><span class="lbl">Proudly sponsored by</span>'
        '<a class="exa" href="https://www.exabeam.com/" target="_blank" rel="noopener" aria-label="Exabeam">'
        f'<img class="exa-logo" src="{esc(home)}assets/exabeam-logo-white.svg" alt="Exabeam" width="187" height="32"></a>'
        '<p class="sponsor-note">Exabeam founded the Open Agent and AI Security Community and supports its '
        'projects with ongoing development — part of its commitment to security in an increasingly agentic world.</p>'
        '</div>'
        '<div class="foot-bottom">'
        '<span>Open Agent and AI Security Community &middot; Open source &middot; built for the community</span>'
        '<span>&copy; 2026 Open Agent and AI Security Community</span>'
        '</div></div></footer>'
    )


def page_shell(title, description, canonical, body_html, home, blog_home, active_blog,
                og_image="", og_image_dims=None, og_type="article",
                keywords="", json_ld="", published_time="", tags=(), robots="index, follow"):
    """og_image should always be set (callers fall back to DEFAULT_OG_IMAGE)
    so every shared blog link — post or index — gets a real preview card on
    Twitter/X and LinkedIn, not a bare title. og_image_dims, when known,
    avoids asserting a wrong width/height for a custom per-post image; when
    None the tags are simply omitted and the crawler sizes the image itself.
    LinkedIn reads only the og:* tags; the twitter:* tags are for X and any
    other twitter-card-aware crawler, kept explicit rather than relying on
    OG fallback for maximum compatibility."""
    if og_image:
        dims_tags = (
            f'<meta property="og:image:width" content="{og_image_dims[0]}">'
            f'<meta property="og:image:height" content="{og_image_dims[1]}">'
            if og_image_dims else ""
        )
        og_image_tags = (
            f'<meta property="og:image" content="{esc(og_image)}">'
            f'{dims_tags}'
            f'<meta name="twitter:card" content="summary_large_image">'
            f'<meta name="twitter:image" content="{esc(og_image)}">'
        )
    else:
        og_image_tags = '<meta name="twitter:card" content="summary">'
    # OG article extension — only meaningful on post pages (published_time set).
    article_tags = "".join(f'<meta property="article:tag" content="{esc(t)}">' for t in tags)
    article_meta = (
        f'<meta property="article:published_time" content="{esc(published_time)}">{article_tags}'
        if published_time else ""
    )
    keywords_tag = f'<meta name="keywords" content="{esc(keywords)}">' if keywords else ""
    json_ld_tag = f'<script type="application/ld+json">{json_ld}</script>' if json_ld else ""
    return (
        f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{esc(title)}</title>'
        f'<meta name="description" content="{esc(description)}">'
        f'{keywords_tag}'
        f'<meta name="robots" content="{esc(robots)}">'
        f'<link rel="canonical" href="{esc(canonical)}">'
        f'<link rel="icon" type="image/png" sizes="32x32" href="{esc(home)}assets/favicon-32.png">'
        f'<link rel="icon" type="image/png" sizes="256x256" href="{esc(home)}assets/favicon-256.png">'
        f'<link rel="apple-touch-icon" sizes="180x180" href="{esc(home)}assets/favicon-180.png">'
        f'<link rel="alternate" type="application/rss+xml" '
        f'title="Open Agent and AI Security Community Blog" href="{esc(blog_home)}feed.xml">'
        f'<link rel="alternate" type="application/feed+json" '
        f'title="Open Agent and AI Security Community Blog (JSON Feed)" href="{esc(blog_home)}feed.json">'
        f'<meta property="og:type" content="{esc(og_type)}">'
        f'<meta property="og:title" content="{esc(title)}">'
        f'<meta property="og:description" content="{esc(description)}">'
        f'<meta property="og:url" content="{esc(canonical)}">'
        f'<meta name="twitter:title" content="{esc(title)}">'
        f'<meta name="twitter:description" content="{esc(description)}">'
        f'{og_image_tags}'
        f'{article_meta}'
        f'{json_ld_tag}'
        f'<link rel="preconnect" href="https://fonts.googleapis.com">'
        f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        f'<style>{CSS}</style>'
        f'{analytics_scripts(home)}'
        f'</head><body>'
        f'{site_header(home, blog_home, active_blog)}'
        f'<main><div class="content">{body_html}</div></main>'
        f'{site_footer(home)}'
        f'{COPY_LINK_JS}'
        f'</body></html>'
    )


def render_post_body(meta, img_rel, related=()):
    tags_html = "".join(f'<span class="tag">{esc(t)}</span>' for t in meta["tags"])
    img = image_url(meta["image"], img_rel)
    hero_html = (f'<img class="post-hero" src="{esc(img)}" alt="{esc(meta["image_alt"])}">'
                 if img else "")
    updated_html = (f' &middot; Updated {human_date(meta["updated"])}'
                    if meta["updated"] and meta["updated"] != meta["date"] else '')
    canonical = f'{SITE}/blog/{meta["slug"]}/'
    draft_html = (
        '<div class="draft-banner"><b>Draft</b> — not yet published. This page '
        'isn\'t linked from the blog index, feeds, or sitemap, and is marked '
        '<code>noindex</code> for search engines.</div>'
        if not meta["published"] else ""
    )
    return (
        draft_html
        + hero_html
        + '<p class="eyebrow">Community blog</p>'
        + f'<h1>{esc(meta["title"])}</h1>'
        + f'<div class="meta">{human_date(meta["date"])}{updated_html} &middot; '
        + f'{esc(meta["author"])} &middot; {meta["reading_time"]} min read'
        + (f' &middot; {tags_html}' if tags_html else '')
        + '</div>'
        + meta["toc_html"]
        + resolve_body_images(meta["body_html"], img_rel)
        + render_share(canonical, meta["title"])
        + render_related(related)
    )


def related_posts(post, posts, limit=3):
    """Other posts sharing at least one tag — most shared tags first, newest
    first as a tiebreak. A post with no tags has nothing to match on, so it
    never gets (or produces) related posts."""
    if not post["tags"]:
        return []
    scored = [(len(set(post["tags"]) & set(p["tags"])), p)
              for p in posts if p is not post and set(post["tags"]) & set(p["tags"])]
    scored.sort(key=lambda t: t[1]["date"], reverse=True)
    scored.sort(key=lambda t: t[0], reverse=True)
    return [p for _, p in scored[:limit]]


def render_related(related):
    if not related:
        return ""
    cards = "".join(
        f'<a class="related-card" href="../{esc(p["slug"])}/">'
        f'<div class="date">{human_date(p["date"])}</div>'
        f'<h3>{esc(p["title"])}</h3></a>'
        for p in related
    )
    return f'<div class="related"><h2>Related posts</h2><div class="related-list">{cards}</div></div>'


def render_share(canonical, title):
    tw = f'https://twitter.com/intent/tweet?text={urllib.parse.quote(title)}&url={urllib.parse.quote(canonical)}'
    li = f'https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(canonical)}'
    return (
        '<div class="share">'
        '<span class="share-label">Share</span>'
        f'<a class="share-btn" href="{esc(tw)}" target="_blank" rel="noopener" aria-label="Share on X">{X_ICON}</a>'
        f'<a class="share-btn" href="{esc(li)}" target="_blank" rel="noopener" aria-label="Share on LinkedIn">{LINKEDIN_ICON}</a>'
        f'<button type="button" class="share-btn copy-link" data-url="{esc(canonical)}">Copy link</button>'
        '</div>'
    )


def render_index_body(posts, img_rel):
    head = (
        '<p class="eyebrow">Open Agent and AI Security Community</p>'
        '<h1><span class="grad">Blog</span></h1>'
        '<p class="meta">Announcements, release notes, and project updates from the community. '
        '&middot; <a href="feed.xml">RSS feed</a> &middot; <a href="feed.json">JSON Feed</a></p>'
    )
    if not posts:
        return head + '<p class="meta">No posts yet — check back soon.</p>'

    # The newest post gets a bigger, more prominent treatment (larger image,
    # larger title, visible summary) instead of sitting in the same compact
    # card as everything else — same idea as scale.com/blog's featured post.
    hero, rest = posts[0], posts[1:]
    hero_summary = hero.get("summary") or strip_tags(hero["body_html"])[:200]
    hero_img = image_url(hero["image"], img_rel)
    hero_thumb_html = f'<img class="hero-thumb" src="{esc(hero_img)}" alt="">' if hero_img else ""
    hero_html = (
        f'<a class="hero-card" href="{esc(hero["slug"])}/">'
        f'{hero_thumb_html}'
        f'<h2>{esc(hero["title"])}</h2>'
        f'<div class="date">{human_date(hero["date"])}</div>'
        f'<p>{esc(hero_summary)}</p>'
        f'</a>'
    )

    cards = []
    for p in rest:
        summary = p.get("summary") or strip_tags(p["body_html"])[:160]
        img = image_url(p["image"], img_rel)
        thumb_html = f'<img class="post-thumb" src="{esc(img)}" alt="">' if img else ""
        cards.append(
            f'<a class="post-card" href="{esc(p["slug"])}/">'
            f'{thumb_html}'
            f'<div class="post-body">'
            f'<div class="date">{human_date(p["date"])}</div>'
            f'<h2>{esc(p["title"])}</h2>'
            f'<p>{esc(summary)}</p>'
            f'</div></a>'
        )
    rest_html = (f'<h2 class="more-label">More from the blog</h2><div class="posts">{"".join(cards)}</div>'
                 if cards else '')

    return f'{head}{hero_html}{rest_html}'


def xml_esc(s):
    return html.escape(str(s), quote=False)


def render_rss(posts):
    """RSS 2.0 (Atom would be equivalent, but RSS is still what most readers
    and aggregation tools default to expecting). dc:creator carries author
    name — RSS's own <author> element wants an email address, which we don't
    have, so this is the standard workaround."""
    items = []
    for p in posts:
        url = f'{SITE}/blog/{p["slug"]}/'
        summary = p.get("summary") or strip_tags(p["body_html"])[:160]
        items.append(
            '<item>'
            f'<title>{xml_esc(p["title"])}</title>'
            f'<link>{xml_esc(url)}</link>'
            f'<guid isPermaLink="true">{xml_esc(url)}</guid>'
            f'<pubDate>{rfc822_date(p["date"])}</pubDate>'
            f'<dc:creator>{xml_esc(p["author"])}</dc:creator>'
            f'<description>{xml_esc(summary)}</description>'
            '</item>'
        )
    last_build = rfc822_date(posts[0]["date"]) if posts else rfc822_date(
        datetime.date.today().isoformat())
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<channel>'
        '<title>Blog — Open Agent and AI Security Community</title>'
        f'<link>{SITE}/blog/</link>'
        f'<atom:link href="{SITE}/blog/feed.xml" rel="self" type="application/rss+xml"/>'
        '<description>Announcements, release notes, and project updates from the '
        'Open Agent and AI Security Community.</description>'
        '<language>en-us</language>'
        f'<lastBuildDate>{last_build}</lastBuildDate>'
        f'{"".join(items)}'
        '</channel></rss>'
    )


def render_json_feed(posts):
    """JSON Feed 1.1 (jsonfeed.org) — a plainer, JSON-native alternative to
    RSS that some modern readers/tools prefer; same underlying post data as
    feed.xml, just a second serialization. content_text (not content_html) is
    used deliberately: the post body's images/links are resolved relative to
    blog/<slug>/, and re-resolving them absolute for a feed consumed out of
    that context is exactly the kind of thing that quietly breaks — plain
    text sidesteps it entirely."""
    items = []
    for p in posts:
        url = f'{SITE}/blog/{p["slug"]}/'
        item = {
            "id": url,
            "url": url,
            "title": p["title"],
            "summary": p.get("summary") or strip_tags(p["body_html"])[:160],
            "content_text": strip_tags(p["body_html"]),
            "date_published": f'{p["date"]}T00:00:00Z',
            "authors": [{"name": p["author"]}],
        }
        if p["updated"] and p["updated"] != p["date"]:
            item["date_modified"] = f'{p["updated"]}T00:00:00Z'
        if p["tags"]:
            item["tags"] = p["tags"]
        items.append(item)
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Blog — Open Agent and AI Security Community",
        "home_page_url": f"{SITE}/blog/",
        "feed_url": f"{SITE}/blog/feed.json",
        "description": "Announcements, release notes, and project updates from the "
                        "Open Agent and AI Security Community.",
        "items": items,
    }
    return json.dumps(feed, ensure_ascii=False, indent=2)


def render_blog_sitemap(posts):
    """This blog's own sitemap — same modular pattern observra/praxen use for
    their sub-sites (see sitemap.xml's own header comment): drop in
    blog/sitemap.xml and add one <sitemap> line to the root index, rather than
    hand-maintaining post URLs inside sitemap-pages.xml where they'd go stale."""
    urls = [f'<url><loc>{SITE}/blog/</loc></url>']
    urls += [f'<url><loc>{SITE}/blog/{p["slug"]}/</loc>'
             f'<lastmod>{p["updated"] or p["date"]}</lastmod></url>' for p in posts]
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'{"".join(urls)}'
        '</urlset>'
    )


def main():
    paths = sorted(glob.glob(os.path.join(POSTS_DIR, "*.md")))
    if not paths:
        sys.exit(f"no posts found in {POSTS_DIR}")

    posts = [parse_post(p) for p in paths]
    posts.sort(key=lambda p: p["date"], reverse=True)
    # The index/feeds/sitemap/JSON-LD/related-posts pool is published posts
    # only — a draft's own page still gets built below (for direct-link QA),
    # but must never leak into anything a published post links to or that a
    # crawler/reader discovers on its own.
    published = [p for p in posts if p["published"]]

    for p in posts:
        out_dir = os.path.join(HERE, p["slug"])
        os.makedirs(out_dir, exist_ok=True)
        description = p.get("summary") or strip_tags(p["body_html"])[:160]
        canonical = f'{SITE}/blog/{p["slug"]}/'
        if not p["image"]:
            og_image, og_image_dims = DEFAULT_OG_IMAGE, DEFAULT_OG_IMAGE_DIMS
        elif IMAGE_URL_RE.match(p["image"]):
            og_image, og_image_dims = p["image"], None
        else:
            og_image = f'{SITE}/blog/images/{p["image"]}'
            og_image_dims = local_image_dimensions(p["image"])
        out_html = page_shell(
            title=f'{p["title"]} — Community Blog',
            description=description,
            canonical=canonical,
            body_html=render_post_body(p, img_rel="../", related=related_posts(p, published)),
            home="../../",
            blog_home="../",
            active_blog=True,
            og_image=og_image,
            og_image_dims=og_image_dims,
            keywords=", ".join(p["tags"]),
            json_ld=json_ld_post(p, canonical, og_image) if p["published"] else "",
            published_time=p["date"],
            tags=p["tags"],
            robots="index, follow" if p["published"] else "noindex, follow",
        )
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(out_html)

    index_html = page_shell(
        title="Blog — Open Agent and AI Security Community",
        description="Announcements, release notes, and project updates from the "
                     "Open Agent and AI Security Community.",
        canonical=f"{SITE}/blog/",
        body_html=render_index_body(published, img_rel=""),
        home="../",
        blog_home="./",
        active_blog=True,
        og_image=DEFAULT_OG_IMAGE,
        og_image_dims=DEFAULT_OG_IMAGE_DIMS,
        og_type="website",
        json_ld=json_ld_index(published),
    )
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index_html)

    with open(os.path.join(HERE, "feed.xml"), "w", encoding="utf-8") as fh:
        fh.write(render_rss(published))

    with open(os.path.join(HERE, "feed.json"), "w", encoding="utf-8") as fh:
        fh.write(render_json_feed(published))

    with open(os.path.join(HERE, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(render_blog_sitemap(published))

    drafts = len(posts) - len(published)
    print(f"Wrote {len(published)} published + {drafts} draft post page(s) "
          f"+ blog/index.html + feed.xml + feed.json + sitemap.xml")


if __name__ == "__main__":
    main()

# Community blog

Static blog for the Open Agent and AI Security Community site. Markdown posts
in `posts/` are compiled by `generate_blog.py` into `index.html` (the
chronological post list) and `<slug>/index.html` per post — the same
"generate locally, commit the output" model as `stats/generate.py`, no
build-on-deploy, no client-side JS.

This file is the reference for **both humans and agents** editing this
folder. If you're an agent adding or editing a post, follow this exactly
rather than inventing a different shape.

## Adding a post

Create `posts/YYYY-MM-DD-slug.md`. The date prefix drives sort order; the
`slug` part (with the date prefix stripped) becomes the post's URL,
`blog/<slug>/`.

```markdown
---
title: Observra 1.1: Any Agent, No Adapter Required
author: Steve Wilson
date: 2026-08-04
summary: One-line teaser shown on the index card and in link previews.
tags: release, observra
image: observra-1.1.jpg
image_alt: Optional alt text; defaults to the post title if omitted.
---

Body starts here, plain Markdown. Start headings at ## (H2) — the post
title itself is the page's only H1, rendered from the `title` field above,
not from anything in the body.
```

| Field        | Required | Notes                                                          |
|--------------|----------|-----------------------------------------------------------------|
| `title`      | yes      | Rendered as the page's H1 and `<title>`.                       |
| `author`     | yes      | Plain text, e.g. `Steve Wilson`.                                |
| `date`       | yes      | `YYYY-MM-DD`. Drives sort order — there's no separate nav to edit. |
| `summary`    | no       | Index-card teaser and `og:description`. Falls back to the first ~160 characters of the rendered post if omitted. |
| `tags`       | no       | Comma-separated, shown as small chips under the title.          |
| `image`      | no       | See **Images** below.                                           |
| `image_alt`  | no       | Alt text for `image`. Defaults to `title`.                      |

The generator hard-fails (exits non-zero, writes nothing) if `title`,
`author`, or `date` is missing, or `date` isn't `YYYY-MM-DD` — fix the post
named in the error rather than working around it.

## Markdown support

Rendered via the `markdown` library with `tables`, `fenced_code`, `toc`, and
`sane_lists` extensions (same dependency/extensions observra and praxen
already pin for their own `docs_build.py` — see that repo's `docs_build.py`
if you want the fuller rationale).

- Start body headings at `##`. Every `##` (H2) automatically appears in an
  on-page table of contents rendered above the post body — no separate TOC
  to maintain. `###` and deeper are fine but don't get a TOC entry.
- Tables, fenced code blocks (` ```lang `), and both ordered/unordered lists
  work as standard Markdown.
- Raw inline HTML passes through if you need it, but reach for it rarely —
  almost everything should be plain Markdown.

## Images

Optional — a post with no `image` field renders as text-only on both the
index card and the post page; nothing to configure to skip it.

- Put image files directly in `blog/images/` (checked into git — these are
  real, deliberate assets, not generated output, unlike everything else in
  `blog/` besides `posts/`).
- Reference by **filename only** in frontmatter: `image: observra-1.1.jpg`.
  A full `https://` URL also works if the image is hosted elsewhere instead.
- One image is used in two places: a full-width header banner on the post
  page, and a thumbnail on that post's index card. There's no separate
  thumbnail field — same file, two crops.
- **Aspect ratio ~2:1** (e.g. 1200×630 — the same shape the rest of the site
  uses for `og:image`). The header banner is `object-fit: cover` at 2:1, so
  a very different ratio will crop in ways you didn't intend; check it after
  building.
- The image doubles as the post's `og:image`/`twitter:image` (the thumbnail
  Slack/LinkedIn/X show when the post link is shared) automatically — no
  separate step. For a local file, its real width/height are read straight
  from the file (PNG/JPEG headers) and included as `og:image:width/height`,
  so the declared size always matches reality rather than asserting a fixed
  1200×630 regardless of the actual file. An external `https://` image has no
  local file to inspect, so those dimension tags are simply omitted — every
  crawler sizes the image itself on fetch regardless, they just don't get the
  hint.
- A post with **no** `image` field still gets a real preview card rather than
  a bare title: it falls back to the same `assets/community-social.png` the
  root site uses. The blog index page uses this same fallback.

## Links

Post pages live two directories deep (`blog/<slug>/index.html`); the blog
index lives one directory deep (`blog/index.html`). Get link paths wrong
here and they look fine locally but 404 once regenerated or moved. Rules of
thumb for links written inside a post body:

- **Site sections / the homepage** (`#mission`, `#projects`, etc.) — use the
  full absolute URL, e.g. `https://open-agent-ai-security.github.io/#projects`.
  Don't hand-write `../../#projects` — it's correct today but silently
  breaks if a post's path ever changes, and it doesn't survive being
  copy-pasted between posts.
- **Another blog post** — relative, one level up: `../other-post-slug/`.
- **Observra / Praxen / any other project site or repo** — the full
  `https://` URL, same as everywhere else on this site.
- **Images** — handled by the `image` frontmatter field (see above), not a
  Markdown `![]()` in the body, unless you're intentionally inlining an
  extra image mid-post (in which case the same relative-path rules apply:
  `../images/foo.jpg` from a post body, since it's rendered one level
  below `blog/`).

## SEO and structured data

Generated automatically per post — nothing to hand-author:

- `<meta name="keywords">` from the post's `tags` (omitted if the post has none).
- Open Graph (`og:*`, including explicit `og:image:width/height` when known)
  + `article:published_time` + `article:tag` per tag. LinkedIn reads these
  exclusively.
- Twitter Card tags (`twitter:card`, `twitter:title`, `twitter:description`,
  `twitter:image`) set explicitly rather than left to X's OG fallback —
  `summary_large_image` since every page always has an image (the post's own,
  or the site default — see **Images** above).
- JSON-LD `BlogPosting` structured data (headline, description, dates, author,
  publisher, image, keywords) on every post page, and a `Blog` + `blogPost[]`
  list on the index page — same GEO intent as the JSON-LD in the root
  `index.html`, scoped to blog content.
- Favicons, canonical URL, and Google Fonts preconnect match the root page.
- `blog/sitemap.xml` is regenerated every run (one `<url>` per post, plus the
  index) and is wired into the root `sitemap.xml` as its own `<sitemap>` entry
  — the same modular pattern observra/praxen use for their own sub-sitemaps.
  Don't hand-add blog URLs to `sitemap-pages.xml`; they'd go stale.

If you add a new frontmatter field that should feed SEO/structured data
(e.g. a canonical external URL for a cross-posted piece), wire it into
`json_ld_post()`/`page_shell()` in `generate_blog.py` — don't hand-edit the
generated `<head>`.

## Web analytics

Every page carries the same two cookieless trackers as the root `index.html`
(`analytics_scripts()` in `generate_blog.py`) — GoatCounter and Cloudflare Web
Analytics, same account/token, just with the asset path adjusted for depth.
This isn't read from `index.html` automatically; if that snippet ever changes
(token rotation, dropping one of the two tools), update `analytics_scripts()`
to match by hand.

## RSS feed

`blog/generate_blog.py` also writes `blog/feed.xml` (RSS 2.0) on every run —
one `<item>` per post, newest first, with `dc:creator` carrying the author
(RSS's own `<author>` element expects an email address, which posts don't
have). It's linked three ways: a visible "RSS feed" link on the blog index,
an `<link rel="alternate" type="application/rss+xml">` autodiscovery tag on
every blog page *and* the root `index.html`, and listed in `llms.txt`. If you
change post fields that should show up in the feed, edit `render_rss()`
alongside the HTML renderers so they don't drift apart.

## Building

```bash
pip install -r requirements-dev.txt   # dev-only: pins `markdown`, nothing runtime ships this
python3 blog/generate_blog.py
```

Regenerates `blog/index.html`, `blog/<slug>/index.html` for every file in
`blog/posts/`, `blog/feed.xml`, and `blog/sitemap.xml`. **Commit the
regenerated output together with the source Markdown in the same change** —
like `stats/generate.py`, this repo doesn't build on deploy; GitHub Pages
just serves whatever's committed.

## Rules for agents specifically

- Never hand-edit anything under `blog/<slug>/`, `blog/index.html`,
  `blog/feed.xml`, or `blog/sitemap.xml` directly — they're all build output
  and get silently overwritten by the next `python3 blog/generate_blog.py`
  run. Edit the source in `blog/posts/*.md` (or `generate_blog.py`/this
  README) and regenerate.
- Always run the generator after adding/editing a post, a template change,
  or a theme tweak, and commit the regenerated output in the same change —
  don't leave `blog/index.html` stale relative to `blog/posts/`.
- Don't invent a `title`, `author`, or `date` on someone's behalf — ask if
  it's unclear rather than guessing.
- Match the existing tone: short, factual, dev-facing — see
  `posts/2026-07-29-welcome-to-the-blog.md` for the reference voice. Avoid
  overwrought marketing copy unless a post is explicitly meant to be one
  (e.g. a press-release-style release announcement).

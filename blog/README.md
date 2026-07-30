# Community blog

Static blog for the Open Agent and AI Security Community site. Markdown posts
in `posts/` are compiled by `generate_blog.py` into `index.html` (the
chronological post list) and `<slug>/index.html` per post — the same
"generate locally, commit the output" model as `stats/generate.py`, no
build-on-deploy. The only JavaScript on any page is the tiny first-party
copy-link handler (see **Share and related posts** below) plus the site's
existing analytics snippet — no third-party embeds, no framework.

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
published: yes
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
| `published`  | no       | `yes`/`true`/`on`/`1` (case-insensitive) to go live; **anything else, including omitting it, is a draft.** See **Draft workflow** below. |
| `updated`    | no       | `YYYY-MM-DD`. Only set this when you materially edit a post after publishing — see **Editing a published post** below. |
| `summary`    | no       | Index-card teaser and `og:description`. Falls back to the first ~160 characters of the rendered post if omitted. |
| `tags`       | no       | Comma-separated, shown as small chips under the title. Also drives **Related posts** (see below). |
| `image`      | no       | See **Images** below.                                           |
| `image_alt`  | no       | Alt text for `image`. Defaults to `title`.                      |

The generator hard-fails (exits non-zero, writes nothing) if `title`,
`author`, or `date` is missing, or `date` isn't `YYYY-MM-DD` — fix the post
named in the error rather than working around it.

## Draft workflow

`published` is how you queue a post — write it, commit it, even push it —
without it going live, then flip one field when it's actually time to launch:

1. **Write the post** with `published` omitted (or set to anything other than
   `yes`/`true`/`on`/`1` — e.g. write `published: no` for clarity if you
   want). Regenerate. The post still gets a real page at `blog/<slug>/`, so
   you (or reviewers) can open it, click through it, check the image/TOC/
   share row — everything renders exactly as it will once live.
2. **A draft page is deliberately excluded from** the blog index, `feed.xml`,
   `feed.json`, `blog/sitemap.xml`, the blog-wide JSON-LD, and every other
   post's **Related posts** list — a live post must never surface a draft's
   title/existence before it's meant to. A draft's own page also carries
   `<meta name="robots" content="noindex, follow">`, and a visible amber
   "Draft" banner at the top of the post so nobody mistakes a QA preview for
   the live thing (including you, three tabs into reviewing a queue of them).
   Its own **Related posts** section still pulls from already-published posts
   only, so that part of the QA preview is accurate too.
3. **When it's launch time**, change `published: no` to `published: yes` in
   that one file and regenerate — the post joins the index/feeds/sitemap/
   JSON-LD/related-posts pool in the same build, no other edits needed. This
   is the "publish on a schedule with launches" step: prep and review the
   post whenever, flip the field the moment you actually want it live.

A draft's file (and its generated `blog/<slug>/index.html`) can still be
committed and pushed like anything else in this repo — being unindexed and
unlinked from every discovery surface is what keeps it effectively private,
not being absent from git or the deployed site.

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

All post images — header, inline, whatever — live in one place and follow
one rule: **put the file in `blog/images/` (checked into git — these are
real, deliberate assets, not generated output, unlike everything else in
`blog/` besides `posts/`), then reference it by filename only.** The
generator resolves a bare filename to the right relative path for wherever
it's actually rendering (`blog/index.html` vs. `blog/<slug>/index.html` are
different depths) — you never hand-write `../images/...` yourself. A full
`https://` URL also works anywhere a filename does, if the image is hosted
elsewhere instead. A post needs neither kind of image; both fall back
cleanly (see below).

### Header / preview image

The optional `image` frontmatter field (see **Adding a post** above):

- One image is used in three places: a full-width header banner on the post
  page, a thumbnail on that post's index card, and the `og:image`/
  `twitter:image` shown when the link is shared — there's no separate field
  for any of those, same file, different crops.
- **Aspect ratio ~2:1** (e.g. 1200×630 — the same shape the rest of the site
  uses for `og:image`). The header banner and index thumbnail are both
  `object-fit: cover` at 2:1, so a very different ratio will crop in ways you
  didn't intend; check it after building.
- For a local file, its real width/height are read straight from the file
  (PNG/JPEG headers) and included as `og:image:width/height`, so the
  declared size always matches reality rather than asserting a fixed
  1200×630 regardless of the actual file. An external `https://` image has
  no local file to inspect, so those dimension tags are simply omitted —
  every crawler sizes the image itself on fetch regardless, they just don't
  get the hint.
- A post with **no** `image` field still gets a real preview card rather
  than a bare title: it falls back to the same `assets/community-social.png`
  the root site uses. The blog index page uses this same fallback.

### Inline images inside a post body

Same `blog/images/` directory, same bare-filename convention — just written
as standard Markdown instead of frontmatter:

```markdown
![OWASP LLM Top 10 coverage by category](praxen-1-2-owasp-coverage.png)
```

The generator resolves the filename the same way it resolves the header
`image` field. A path you've already written yourself — absolute (`/...`),
explicitly relative (`./...`/`../...`), or a full `https://` URL — is left
untouched, so you can opt out of the convention if you genuinely need to.
No aspect-ratio requirement here (it isn't cropped to a fixed box like the
header image); it just renders at its natural size, capped to the content
column's width.

Naming tip: `blog/images/` is one flat directory shared by every post, not
one folder per post — prefix a body image's filename with the post's slug
(e.g. `praxen-1-2-owasp-coverage.png`, not `owasp-coverage.png`) so two
posts never collide on a generic name.

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
- **Images** — a bare filename, in frontmatter or in a Markdown `![]()`; see
  **Images** above. The generator resolves the path for you either way, so
  this is the one category of link where you don't apply the depth rules
  above yourself.

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

## Feeds — RSS and JSON Feed

`blog/generate_blog.py` writes two feeds on every run, from the same post
data:

- **`blog/feed.xml`** (RSS 2.0) — one `<item>` per post, newest first, with
  `dc:creator` carrying the author (RSS's own `<author>` element expects an
  email address, which posts don't have).
- **`blog/feed.json`** ([JSON Feed 1.1](https://www.jsonfeed.org/version/1.1/))
  — a plainer JSON-native alternative some modern readers/tools prefer. Uses
  `content_text` rather than `content_html` on purpose: a post body's
  images/links are resolved relative to `blog/<slug>/`, and re-resolving them
  absolute for a feed read out of that context is exactly the kind of thing
  that quietly breaks — plain text sidesteps it entirely.

Both are linked from the blog index (visible "RSS feed"/"JSON Feed" links)
and via `<link rel="alternate">` autodiscovery on every blog page. At launch,
the root `index.html` is meant to carry the same two autodiscovery tags plus
a "Blog" nav link — both are already written out as HTML comments at their
exact intended spot in `index.html` (search `withheld`), ready to uncomment.
Right now they're deliberately commented out: the blog is in QA/preview and
intentionally unlinked from the main page until that's done (see this repo's
git history for why). It's still listed in `llms.txt` regardless, since
that's a separate discovery surface with no "is this launched yet" gate.
If you add a post field that should show up in a feed, update `render_rss()`
**and** `render_json_feed()` together so they don't
drift apart.

## Share and related posts

Every post page (not the index) gets two things at the bottom, generated
automatically:

- **Share row** — plain-href links to X and LinkedIn's share-intent URLs
  (no embedded widgets, no tracking beyond what those platforms' own pages
  do), plus a "Copy link" button. The button is the one place this blog uses
  JavaScript: a single small first-party script (`COPY_LINK_JS` in
  `generate_blog.py`) using `navigator.clipboard`, delegated on `document` so
  it's one script tag total, harmless on pages with no button. Nothing
  external is loaded to make it work.
- **Related posts** — up to 3 other posts sharing at least one `tags` value,
  ranked by most shared tags then newest first. A post with no tags gets (and
  is eligible to appear in) no related-posts section — there's no fallback
  "recent posts" list standing in for it.

Reading time (`meta["reading_time"]`, shown as "N min read" next to the
byline) is computed from the rendered post's word count at ~200wpm, rounded
up, minimum 1 — not configurable, just recomputed every build.

## Editing a published post

Set the optional `updated` frontmatter field (`YYYY-MM-DD`) when you
materially edit a post after it's already live — a typo fix doesn't need it,
a real content change does. It shows as "Updated ..." next to the publish
date, and feeds `dateModified` in the post's JSON-LD, `date_modified` in its
JSON Feed entry, and `<lastmod>` in `blog/sitemap.xml` (which otherwise
silently keeps reusing the original publish date forever, even after real
edits). Omit it and nothing changes — this is purely additive.

## Building

```bash
pip install -r requirements-dev.txt   # dev-only: pins `markdown`, nothing runtime ships this
python3 blog/generate_blog.py
```

Regenerates `blog/index.html`, `blog/<slug>/index.html` for every file in
`blog/posts/`, `blog/feed.xml`, `blog/feed.json`, and `blog/sitemap.xml`.
**Commit the regenerated output together with the source Markdown in the
same change** — like `stats/generate.py`, this repo doesn't build on
deploy; GitHub Pages just serves whatever's committed.

## Rules for agents specifically

- Never hand-edit anything under `blog/<slug>/`, `blog/index.html`,
  `blog/feed.xml`, `blog/feed.json`, or `blog/sitemap.xml` directly — they're
  all build output and get silently overwritten by the next
  `python3 blog/generate_blog.py` run. Edit the source in `blog/posts/*.md`
  (or `generate_blog.py`/this README) and regenerate.
- Always run the generator after adding/editing a post, a template change,
  or a theme tweak, and commit the regenerated output in the same change —
  don't leave `blog/index.html` stale relative to `blog/posts/`.
- Don't invent a `title`, `author`, or `date` on someone's behalf — ask if
  it's unclear rather than guessing.
- Match the existing tone: short, factual, dev-facing — see
  `posts/2026-07-29-observra-1-1-release.md` for the reference voice. Avoid
  overwrought marketing copy unless a post is explicitly meant to be one
  (e.g. a press-release-style release announcement).
- New posts default to draft (`published` omitted) unless told otherwise —
  don't set `published: yes` on someone's behalf. Flipping it is a real
  "make this public" action, same category as pushing to `main`: only do it
  when explicitly asked to publish/launch, not as part of routine drafting
  or editing.
- Same goes for the commented-out nav link and autodiscovery tags in the
  root `index.html` (search `withheld`) — don't uncomment them until
  explicitly asked to launch the blog off of QA/preview.

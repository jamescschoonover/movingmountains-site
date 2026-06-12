#!/usr/bin/env python3
"""build_blog.py — Moving Mountains Community blog generator.

Markdown in -> themed static HTML out, matching the site's mountain theme (theme.css).
One broad blog, many categories. Write a post as markdown in content/blog/<slug>.md with
frontmatter, run this, and push (same Cloudflare Pages deploy as the rest of the site).

  content/blog/big-boy-hornell.md   ->   blog/big-boy-hornell/index.html
                                          blog/index.html        (all posts, category filter)
                                          blog/feed.xml          (RSS)

Frontmatter (between --- lines):
  title:    Big Boy 4014 Rolls Into Hornell
  date:     2026-06-12                  (YYYY-MM-DD; sorts newest-first)
  category: Adventures                  (free text; becomes a filter chip)
  summary:  One line for the card + meta description + RSS.
  cover:    /assets/blog/big-boy-hornell/cover.jpg   (optional hero/card image)
  author:   James                       (optional; default "Moving Mountains Community")
  draft:    true                        (optional; skipped from the build)

Markdown supported: # ## ### headings, **bold**, *italic*, [links](url), `code`,
- bullet lists, 1. numbered lists, > quotes, --- rules, and image lines
  ![caption text](/assets/blog/<slug>/photo.jpg)  -> figure with caption.

Dependency-free (stdlib only) so it deploys anywhere.
"""
import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SITE = Path(__file__).resolve().parent
CONTENT = SITE / "content" / "blog"
OUT = SITE / "blog"
SITE_URL = "https://movingmountains.community"
DEFAULT_AUTHOR = "Moving Mountains Community"

# The shared mountain-range hero SVG (copied 1:1 from the site so the blog feels native).
RANGE_SVG = """  <svg class="range" viewBox="0 0 1440 560" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
    <defs>
      <linearGradient id="mmsky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#284a62"/><stop offset="52%" stop-color="#3a4f49"/><stop offset="100%" stop-color="#1d4434"/>
      </linearGradient>
      <radialGradient id="mmsun" cx="50%" cy="50%" r="50%">
        <stop offset="0" stop-color="#ffe9c2" stop-opacity=".9"/><stop offset="100%" stop-color="#ffe9c2" stop-opacity="0"/>
      </radialGradient>
    </defs>
    <rect width="1440" height="560" fill="url(#mmsky)"/>
    <circle cx="1085" cy="148" r="120" fill="url(#mmsun)"/>
    <circle cx="1085" cy="148" r="42" fill="#f6cf8e"/>
    <g class="birds" fill="#15301f" opacity=".5">
      <path transform="translate(330,150)" d="M0,0 C8,-7 14,-7 22,-1 C14,-3 9,-3 0,3 C-9,-3 -14,-3 -22,-1 C-14,-7 -8,-7 0,0 Z"/>
      <path transform="translate(468,122) scale(.66)" d="M0,0 C8,-7 14,-7 22,-1 C14,-3 9,-3 0,3 C-9,-3 -14,-3 -22,-1 C-14,-7 -8,-7 0,0 Z"/>
    </g>
    <path fill="#3a566b" d="M0,322 L190,262 L360,330 L540,266 L720,330 L900,270 L1080,330 L1260,268 L1440,326 L1440,560 L0,560 Z"/>
    <path fill="#2b4651" d="M0,400 L210,344 L400,408 L590,352 L780,414 L980,350 L1160,410 L1330,356 L1440,400 L1440,560 L0,560 Z"/>
    <path fill="#1d352f" d="M0,470 L240,410 L470,476 L690,428 L910,484 L1130,424 L1330,476 L1440,448 L1440,560 L0,560 Z"/>
    <path fill="#11231f" d="M0,524 L160,508 L320,528 L480,506 L640,530 L800,510 L960,530 L1120,508 L1280,528 L1440,510 L1440,560 L0,560 Z"/>
  </svg>"""

TORN = ('  <div class="torn"><svg viewBox="0 0 1440 46" preserveAspectRatio="none">'
        '<path fill="#f7f3ea" d="M0,46 L0,20 C70,8 130,30 210,18 C300,5 360,28 450,16 C540,6 610,30 700,20 '
        'C800,9 860,30 950,18 C1050,6 1110,28 1200,17 C1290,7 1360,26 1440,16 L1440,46 Z"/></svg></div>')

NAV = """<nav id="nav">
  <a class="brand" href="/">
    <img src="/assets/round-logo.png" alt="Moving Mountains Community — eagle crest">
    <b>Moving Mountains</b>
  </a>
  <button class="nav-toggle" id="navToggle" aria-label="Open menu" aria-expanded="false"><span></span><span></span><span></span></button>
  <div class="nav-links" id="navLinks">
    <a href="/">Home</a>
    <a href="/blog">Blog</a>
    <a href="/links">All Links</a>
    <a href="/james">James</a>
    <a href="/kalli">Kalli</a>
    <a href="/fit">Fit</a>
    <a href="/shop" class="nav-cta">Shop &rarr;</a>
  </div>
</nav>"""

FOOTER = """<footer>
  <div class="foot-in">
    <a class="foot-brand" href="/"><img src="/assets/round-logo.png" alt="Moving Mountains crest"><b>Moving Mountains</b></a>
    <div class="foot-links">
      <a href="/">Home</a>
      <a href="/blog">Blog</a>
      <a href="/shop">Shop</a>
      <a href="mailto:support@movingmountains.community">Contact</a>
    </div>
  </div>
  <div class="foot-fine">&copy; 2026 Moving Mountains Community &middot; Fighting debt. Building the business. Leveling up together.</div>
</footer>"""


def head(title, desc, url, image=None):
    img = image or "/assets/banner1.png"
    if img.startswith("/"):
        img = SITE_URL + img
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{img}">
<link rel="alternate" type="application/rss+xml" title="Moving Mountains Community Blog" href="/blog/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;600;700&family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,400&family=Nunito+Sans:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/theme.css">
<link rel="icon" type="image/png" href="/assets/round-logo.png">
<link rel="apple-touch-icon" href="/assets/round-logo.png">
</head>
<body>
<div class="grain"></div>
{NAV}
"""


def parse_frontmatter(text):
    meta = {}
    if text.lstrip().startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
            return meta, parts[2].strip()
    return meta, text.strip()


def _inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    return t


_BLOCK_START = re.compile(r'^(#{1,4}\s|>|[-*]\s|\d+\.\s|---\s*$|\*\*\*\s*$|!\[)')


def md_to_html(md):
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.lstrip().startswith("<"):            # raw HTML block (video / iframe embeds) — pass through
            buf = []
            while i < len(lines) and lines[i].strip():
                buf.append(lines[i]); i += 1
            out.append("\n".join(buf)); continue
        h = re.match(r'^(#{1,4})\s+(.*)$', line)
        if h:
            lvl = max(2, min(len(h.group(1)), 4))     # h1 reserved for hero: ## -> h2, ### -> h3
            out.append(f"<h{lvl}>{_inline(h.group(2))}</h{lvl}>"); i += 1; continue
        if re.match(r'^(---|\*\*\*)\s*$', line):
            out.append("<hr>"); i += 1; continue
        img = re.match(r'^!\[([^\]]*)\]\(([^)]+?)(?:\s+"([^"]*)")?\)\s*$', line)
        if img:
            alt, src, cap = img.group(1), img.group(2), img.group(3)
            caption = cap or alt
            fig = f'<figure><img src="{src}" alt="{html.escape(alt)}" loading="lazy">'
            if caption:
                fig += f'<figcaption>{html.escape(caption)}</figcaption>'
            out.append(fig + "</figure>"); i += 1; continue
        if line.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                buf.append(lines[i].lstrip()[1:].strip()); i += 1
            out.append("<blockquote>" + _inline(" ".join(buf)) + "</blockquote>"); continue
        if re.match(r'^[-*]\s+', line):
            buf = []
            while i < len(lines) and re.match(r'^[-*]\s+', lines[i].rstrip()):
                buf.append(_inline(re.sub(r'^[-*]\s+', '', lines[i].rstrip()))); i += 1
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in buf) + "</ul>"); continue
        if re.match(r'^\d+\.\s+', line):
            buf = []
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i].rstrip()):
                buf.append(_inline(re.sub(r'^\d+\.\s+', '', lines[i].rstrip()))); i += 1
            out.append("<ol>" + "".join(f"<li>{x}</li>" for x in buf) + "</ol>"); continue
        buf = []
        while i < len(lines) and lines[i].strip() and not _BLOCK_START.match(lines[i].rstrip()):
            buf.append(lines[i].rstrip()); i += 1
        out.append("<p>" + _inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


def fmt_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%B %-d, %Y")
    except Exception:
        return d


def read_time(md):
    words = len(re.findall(r"\w+", md))
    return max(1, round(words / 200))


def render_post(p):
    url = f"{SITE_URL}/blog/{p['slug']}"
    cover = ""
    if p.get("cover"):
        cover = (f'<figure class="cover"><img src="{p["cover"]}" alt="{html.escape(p["title"])}" '
                 f'loading="lazy"></figure>')
    body = md_to_html(p["body"])
    doc = head(f"{p['title']} — Moving Mountains Community", p.get("summary", ""), url, p.get("cover"))
    doc += f"""
<header class="pagehero blog-hero">
{RANGE_SVG}
  <div class="ph-inner">
    <div class="ph-eyebrow reveal">{html.escape(p.get('category', 'Journal'))}</div>
    <h1 class="ph-title reveal d1">{html.escape(p['title'])}</h1>
    <div class="ph-handle reveal d2">{fmt_date(p['date'])} &middot; {read_time(p['body'])} min read &middot; {html.escape(p.get('author', DEFAULT_AUTHOR))}</div>
  </div>
{TORN}
</header>

<main>
  <article class="article reveal">
    {cover}
    {body}
    <hr>
    <p class="backlink"><a href="/blog">&larr; All posts</a> &nbsp;·&nbsp; <a href="/shop">Shop our finds &rarr;</a></p>
  </article>
  <div class="signoff">
    <div class="big reveal">Keep climbing.</div>
    <div class="fam reveal">— Moving Mountains Community 🏔️</div>
  </div>
</main>
{FOOTER}
<script src="/assets/theme.js" defer></script>
</body>
</html>
"""
    return doc


def render_index(posts):
    cats = []
    for p in posts:
        c = p.get("category", "Journal")
        if c not in cats:
            cats.append(c)
    chips = '<button class="catbtn active" data-cat="all">All</button>' + "".join(
        f'<button class="catbtn" data-cat="{html.escape(c)}">{html.escape(c)}</button>' for c in cats)
    cards = []
    for p in posts:
        cov = (f'<img class="pc-cover" src="{p["cover"]}" alt="{html.escape(p["title"])}" loading="lazy">'
               if p.get("cover") else '')
        cards.append(f"""    <a class="postcard reveal" href="/blog/{p['slug']}" data-cat="{html.escape(p.get('category','Journal'))}">
      {cov}
      <div class="pc-body">
        <div class="pc-cat">{html.escape(p.get('category','Journal'))}</div>
        <div class="pc-ti">{html.escape(p['title'])}</div>
        <div class="pc-su">{html.escape(p.get('summary',''))}</div>
        <div class="pc-date">{fmt_date(p['date'])} &middot; {read_time(p['body'])} min read</div>
      </div>
    </a>""")
    empty = '<p style="text-align:center;color:var(--ink-soft);padding:30px">No posts yet — first one&rsquo;s coming. 🏔️</p>'
    doc = head("Blog — Moving Mountains Community",
               "Stories from Moving Mountains Community — adventures, thrift finds, family, and the climb.",
               f"{SITE_URL}/blog")
    doc += f"""
<header class="pagehero blog-hero">
{RANGE_SVG}
  <div class="ph-inner">
    <div class="ph-eyebrow reveal">The Trail Journal</div>
    <h1 class="ph-title reveal d1">Our Blog</h1>
    <p class="ph-bio reveal d2">Adventures, thrift finds, family, and the climb &mdash; from the Moving Mountains Community crew.</p>
  </div>
{TORN}
</header>

<main>
  <div class="catfilter reveal">{chips}</div>
  <div class="bloggrid">
{chr(10).join(cards) if cards else empty}
  </div>
</main>
{FOOTER}
<script src="/assets/theme.js" defer></script>
<script>
（function(){{
  const btns=[...document.querySelectorAll('.catbtn')], cards=[...document.querySelectorAll('.postcard')];
  btns.forEach(b=>b.addEventListener('click',()=>{{
    btns.forEach(x=>x.classList.remove('active')); b.classList.add('active');
    const c=b.dataset.cat;
    cards.forEach(card=>{{card.style.display=(c==='all'||card.dataset.cat===c)?'':'none';}});
  }}));
}})();
</script>
</body>
</html>
"""
    return doc.replace("（function(){", "(function(){")  # guard against any smart-paren


def render_rss(posts):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for p in posts:
        link = f"{SITE_URL}/blog/{p['slug']}"
        try:
            pub = datetime.strptime(p["date"], "%Y-%m-%d").strftime("%a, %d %b %Y 08:00:00 +0000")
        except Exception:
            pub = now
        items.append(f"""    <item>
      <title>{html.escape(p['title'])}</title>
      <link>{link}</link>
      <guid>{link}</guid>
      <category>{html.escape(p.get('category','Journal'))}</category>
      <pubDate>{pub}</pubDate>
      <description>{html.escape(p.get('summary',''))}</description>
    </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Moving Mountains Community — Blog</title>
  <link>{SITE_URL}/blog</link>
  <description>Adventures, thrift finds, family, and the climb.</description>
  <language>en-us</language>
  <lastBuildDate>{now}</lastBuildDate>
{chr(10).join(items)}
</channel></rss>
"""


def main():
    CONTENT.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    posts = []
    for f in sorted(CONTENT.glob("*.md")):
        meta, body = parse_frontmatter(f.read_text(encoding="utf-8"))
        if str(meta.get("draft", "")).lower() == "true":
            print(f"  (skip draft: {f.name})"); continue
        if not meta.get("title") or not meta.get("date"):
            print(f"  ⚠ {f.name}: missing title/date — skipped"); continue
        meta["slug"] = meta.get("slug") or f.stem
        meta["body"] = body
        posts.append(meta)
    posts.sort(key=lambda p: p["date"], reverse=True)
    for p in posts:
        d = OUT / p["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(render_post(p), encoding="utf-8")
        print(f"  ✓ blog/{p['slug']}/  — {p['title']}")
    (OUT / "index.html").write_text(render_index(posts), encoding="utf-8")
    (OUT / "feed.xml").write_text(render_rss(posts), encoding="utf-8")
    print(f"\nBuilt {len(posts)} post(s) + blog/index.html + blog/feed.xml")


if __name__ == "__main__":
    sys.exit(main())

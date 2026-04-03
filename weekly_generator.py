#!/usr/bin/env python3
"""
Weekly blog generator for MAXX Pro Painting and Home Repairs LLC
Runs every Friday at 8am via Railway cron.
Generates 3 SEO blog posts and pushes to GitHub.

Usage:
  python3 weekly_generator.py
  python3 weekly_generator.py --niche "..." --n 3
"""
import os, sys, json, re, subprocess, tempfile, shutil, argparse
from datetime import date
import anthropic

# ── constants ──────────────────────────────────────────────────────────────────
SITE_URL     = "https://maxxprollc.com"
GITHUB_REPO  = os.environ.get("GITHUB_REPO",  "PalmettoAI/MAXX-Pro")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
BLOG_NICHE   = os.environ.get("BLOG_NICHE",
    "Lexington and Columbia SC painting contractors, home repair services, "
    "finish carpentry, flooring installation, small home improvements, "
    "and residential electrical work for homeowners")

SERVICE_PAGES = {
    "interior-painting":      "../interior-painting.html",
    "exterior-painting":      "../exterior-painting.html",
    "carpentry-trim":         "../carpentry-trim.html",
    "drywall-repair":         "../drywall-repair.html",
    "home-repairs":           "../home-repairs.html",
    "residential-electrical": "../residential-electrical.html",
}

SYSTEM_STRATEGIST = """You are an SEO content strategist for MAXX Pro Painting and Home Repairs LLC,
a licensed contractor serving Lexington and Columbia, SC.

Your job: generate blog post metadata (titles, slugs, keywords, excerpts) that rank on Google
for homeowners searching for painting, carpentry, flooring, electrical, and home repair services
in the Lexington/Columbia SC area.

Rules:
- Target long-tail keywords specific to Lexington SC or Columbia SC
- Titles must be specific and useful — never clickbait
- Slugs: lowercase, hyphens only, include a location keyword
- Excerpt: 1-2 sentences, include primary keyword naturally
- Topics must be genuinely distinct — no repeating angles already covered
- Service focus must vary across the 3 posts (never 3 painting posts in one batch)"""

SYSTEM_WRITER = """You are a professional content writer for MAXX Pro Painting and Home Repairs LLC,
a licensed contractor in Lexington and Columbia, SC.

Write blog posts that:
- Open with a specific, concrete hook about a real homeowner problem.
  NEVER start with filler like "When it comes to...", "Are you looking for...",
  "If you're a homeowner...", or "In today's world..."
- Include the primary keyword naturally in the opening paragraph
- Have minimum 4 H2 sections with specific, useful subheadings
- Include at least one <ul> list with practical tips or numbered steps
- Include at least one callout box: <div class="callout"><strong>Pro Tip:</strong> ...</div>
- Use 2-4 internal links with descriptive anchor text — never "click here"
- Close with a specific, action-oriented paragraph mentioning MAXX Pro by name and offering a free estimate
- Write at a friendly expert level — knowledgeable but accessible to homeowners
- Mention Lexington SC or Columbia SC naturally at least twice
- Primary keyword appears in the opening paragraph, at least one H2, and 3-5x total
- Minimum 600 words"""


# ── helpers ────────────────────────────────────────────────────────────────────
def get_client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def slugify(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "-", text.lower())).strip("-")


def extract_published_context(publish_log_path):
    """Return summary of already-published titles/topics to prevent repetition."""
    if not os.path.exists(publish_log_path):
        return "No posts published yet."
    with open(publish_log_path) as f:
        entries = json.load(f)
    if not entries:
        return "No posts published yet."
    lines = [f"- {e.get('title', '')} (topic: {e.get('topic', '')})"
             for e in entries[-20:]]
    return "Already published:\n" + "\n".join(lines)


def clone_repo(tmpdir):
    """Clone repo fresh using GITHUB_TOKEN."""
    repo_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
    subprocess.run(["git", "clone", "--depth=1", repo_url, tmpdir], check=True)


def git_push(repo_dir, message):
    """Stage all, commit, and push. Returns True if anything was pushed."""
    env = os.environ.copy()
    subprocess.run(["git", "-C", repo_dir, "config", "user.email", "bot@maxxprollc.com"],
                   check=True, env=env)
    subprocess.run(["git", "-C", repo_dir, "config", "user.name", "MAXX Pro Bot"],
                   check=True, env=env)
    subprocess.run(["git", "-C", repo_dir, "add", "-A"], check=True, env=env)
    result = subprocess.run(["git", "-C", repo_dir, "diff", "--cached", "--quiet"], env=env)
    if result.returncode == 0:
        print("  No changes to commit.")
        return False
    subprocess.run(["git", "-C", repo_dir, "commit", "-m", message], check=True, env=env)
    subprocess.run(["git", "-C", repo_dir, "push"], check=True, env=env)
    return True


# ── LLM calls — two separate calls per spec ────────────────────────────────────
def generate_metadata(client, niche, published_context, n=3):
    """Call 1: metadata only. Returns list of dicts."""
    prompt = f"""Niche: {niche}

{published_context}

Generate exactly {n} blog post ideas. Return a JSON array only — no markdown fences, no other text:
[
  {{
    "title": "...",
    "slug": "...",
    "keyword": "...",
    "excerpt": "...",
    "topic": "...",
    "service_page": "one of: interior-painting | exterior-painting | carpentry-trim | drywall-repair | home-repairs | residential-electrical | null"
  }}
]"""
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_STRATEGIST,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
    return json.loads(raw.strip())


def generate_post_body(client, meta, niche):
    """Call 2: raw HTML body content only — no head/nav/footer."""
    service_hint = ""
    sp = meta.get("service_page")
    if sp and sp in SERVICE_PAGES:
        label = sp.replace("-", " ").title()
        href  = SERVICE_PAGES[sp]
        service_hint = (
            f'Include a natural internal link to '
            f'<a href="{href}">{label}</a> and 1-2 other service pages.'
        )

    prompt = f"""Write the HTML body content for this blog post.

Title: {meta['title']}
Primary keyword: {meta['keyword']}
Excerpt: {meta['excerpt']}
Business niche: {niche}
{service_hint}

Return ONLY the inner HTML — start directly with an opening <p> tag.
Include H2 sections, lists, callout divs, and internal links.
Do NOT include <html>, <head>, <body>, <nav>, or <footer> tags.
Do NOT wrap output in a JSON string or markdown code fences."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_WRITER,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


# ── HTML builders ──────────────────────────────────────────────────────────────
def build_post_html(meta, body_html, post_date):
    slug    = meta["slug"]
    title   = meta["title"]
    excerpt = meta["excerpt"]
    sp      = meta.get("service_page") or "home-repairs"
    tag     = sp.replace("-", " ").title()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | MAXXPRO Painting and Home Repairs LLC</title>
    <meta name="description" content="{excerpt}">
    <link rel="icon" type="image/png" href="../assets/logo.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Barlow:ital,wght@0,300;0,400;0,500;0,600;1,300&family=Barlow+Condensed:wght@600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --red: #CC0000; --red-bright: #E31515; --black: #080808;
            --surface: #0f0f0f; --surface-2: #161616; --surface-3: #1e1e1e;
            --chrome: #C8C8C8; --chrome-hi: #EFEFEF; --white: #FFFFFF; --muted: #787878;
            --font-display: 'Oswald', sans-serif; --font-body: 'Barlow', sans-serif;
            --ease: cubic-bezier(0.4,0,0.2,1); --dur: 0.3s;
        }}
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html {{ scroll-behavior: smooth; }}
        body {{ background: var(--black); color: var(--chrome-hi); font-family: var(--font-body); line-height: 1.7; overflow-x: hidden; }}
        img {{ max-width: 100%; display: block; }}
        a {{ text-decoration: none; color: inherit; }}
        ul {{ list-style: none; }}
        #nav {{
            position: fixed; top: 0; left: 0; right: 0; z-index: 200;
            display: flex; align-items: center; justify-content: space-between;
            padding: 0.85rem 2.5rem;
            background: rgba(8,8,8,0.95); backdrop-filter: blur(16px);
            border-bottom: 1px solid rgba(204,0,0,0.2);
        }}
        .nav-logo {{ height: 54px; width: auto; max-width: 180px; flex-shrink: 0; }}
        .nav-links {{ display: flex; align-items: center; gap: 2.5rem; }}
        .nav-links a {{ font-family: var(--font-display); font-size: 0.8rem; font-weight: 500; letter-spacing: 0.15em; text-transform: uppercase; color: var(--chrome); transition: color var(--dur) var(--ease); }}
        .nav-links a:hover {{ color: var(--red-bright); }}
        .nav-links .nav-cta {{ background: var(--red); color: var(--white); padding: 0.5rem 1.4rem; clip-path: polygon(8px 0%,100% 0%,calc(100% - 8px) 100%,0% 100%); }}
        .hamburger {{ display: none; flex-direction: column; gap: 5px; cursor: pointer; padding: 6px; background: none; border: none; }}
        .hamburger span {{ display: block; width: 22px; height: 2px; background: var(--chrome-hi); }}
        .article-wrap {{ max-width: 800px; margin: 0 auto; padding: 140px 2rem 5rem; }}
        .post-tag {{ display: inline-block; font-family: var(--font-display); font-size: 0.65rem; letter-spacing: 0.3em; text-transform: uppercase; color: var(--red-bright); margin-bottom: 1rem; }}
        .post-title {{ font-family: var(--font-display); font-size: clamp(1.8rem, 4vw, 3rem); font-weight: 700; text-transform: uppercase; color: var(--chrome-hi); line-height: 1.15; margin-bottom: 0.75rem; }}
        .post-date {{ font-size: 0.8rem; color: var(--muted); margin-bottom: 2rem; }}
        .post-excerpt {{ font-size: 1.1rem; color: var(--chrome); font-weight: 300; margin-bottom: 2.5rem; padding-bottom: 2rem; border-bottom: 1px solid rgba(204,0,0,0.2); }}
        .post-body h2 {{ font-family: var(--font-display); font-size: clamp(1.3rem, 2.5vw, 1.9rem); font-weight: 700; text-transform: uppercase; color: var(--chrome-hi); margin: 2.5rem 0 1rem; }}
        .post-body p {{ color: var(--chrome); margin-bottom: 1.2rem; font-size: 1rem; line-height: 1.75; }}
        .post-body ul {{ list-style: disc; padding-left: 1.5rem; margin-bottom: 1.2rem; }}
        .post-body ul li {{ color: var(--chrome); margin-bottom: 0.4rem; line-height: 1.65; }}
        .post-body a {{ color: var(--red-bright); text-decoration: underline; text-underline-offset: 3px; }}
        .callout {{ background: var(--surface-2); border-left: 3px solid var(--red); padding: 1rem 1.25rem; margin: 1.5rem 0; border-radius: 0 4px 4px 0; }}
        .callout strong {{ color: var(--red-bright); }}
        .cta-section {{ background: var(--red); padding: 4rem 2rem; text-align: center; }}
        .cta-section h2 {{ font-family: var(--font-display); font-size: clamp(1.8rem,4vw,3rem); font-weight: 700; text-transform: uppercase; color: var(--white); margin-bottom: 0.75rem; }}
        .cta-section p {{ color: rgba(255,255,255,0.82); margin-bottom: 2rem; }}
        .btn {{ display: inline-flex; align-items: center; gap: 0.5rem; font-family: var(--font-display); font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; padding: 0.95rem 2rem; clip-path: polygon(10px 0%,100% 0%,calc(100% - 10px) 100%,0% 100%); cursor: pointer; border: none; font-size: 0.875rem; transition: background var(--dur) var(--ease); }}
        .btn-white {{ background: var(--white); color: var(--red); }}
        .btn-white:hover {{ opacity: 0.9; }}
        footer {{ background: #050505; padding: 2rem 2.5rem; border-top: 1px solid rgba(204,0,0,0.15); text-align: center; }}
        footer p {{ font-size: 0.72rem; color: rgba(120,120,120,0.5); }}
        footer a {{ color: var(--red); }}
        @media (max-width: 768px) {{
            #nav {{ padding: 0.65rem 1.25rem; }}
            .nav-logo {{ height: 46px; }}
            .nav-links {{ position: fixed; top: 70px; left: 0; right: 0; background: rgba(8,8,8,0.98); flex-direction: column; align-items: flex-start; padding: 1.5rem 2rem; gap: 1.5rem; transform: translateY(-110%); transition: transform 0.35s var(--ease); visibility: hidden; border-bottom: 1px solid rgba(204,0,0,0.2); }}
            .nav-links.open {{ transform: translateY(0); visibility: visible; }}
            .hamburger {{ display: flex; }}
        }}
    </style>
</head>
<body>
<nav id="nav" role="navigation" aria-label="Main navigation">
    <a href="../index.html" aria-label="MAXXPRO Home">
        <img src="../assets/logo.png" alt="MAXXPRO Painting and Home Repairs LLC" class="nav-logo">
    </a>
    <ul class="nav-links" id="navLinks" role="menubar">
        <li role="none"><a href="../index.html#services" role="menuitem">Services</a></li>
        <li role="none"><a href="../about.html" role="menuitem">About</a></li>
        <li role="none"><a href="../gallery.html" role="menuitem">Gallery</a></li>
        <li role="none"><a href="../reviews.html" role="menuitem">Reviews</a></li>
        <li role="none"><a href="index.html" role="menuitem">Blog</a></li>
        <li role="none"><a href="../index.html#contact" class="nav-cta" role="menuitem">Free Estimate</a></li>
    </ul>
    <button class="hamburger" id="hamburger" aria-label="Toggle menu" aria-expanded="false" onclick="toggleNav()">
        <span></span><span></span><span></span>
    </button>
</nav>

<div class="article-wrap">
    <span class="post-tag">{tag}</span>
    <h1 class="post-title">{title}</h1>
    <p class="post-date">{post_date}</p>
    <p class="post-excerpt">{excerpt}</p>
    <div class="post-body">
{body_html}
    </div>
</div>

<div class="cta-section">
    <h2>Ready to Get Started?</h2>
    <p>Get your free, no-obligation estimate — we come to you anywhere in Lexington or Columbia, SC.</p>
    <a href="../index.html#contact" class="btn btn-white">Get Free Estimate</a>
</div>

<footer>
    <p>&copy; 2025 MAXXPRO Painting and Home Repairs LLC. All rights reserved. | Built by <a href="https://palmettoaiautomation.com" target="_blank" rel="noopener noreferrer">PalmettoAI Automation</a></p>
</footer>
<script>
    function toggleNav() {{
        const links = document.getElementById('navLinks');
        const btn = document.getElementById('hamburger');
        const isOpen = links.classList.toggle('open');
        btn.setAttribute('aria-expanded', isOpen);
    }}
    document.querySelectorAll && document.querySelectorAll('.nav-links a').forEach(link => {{
        link.addEventListener('click', () => {{
            document.getElementById('navLinks').classList.remove('open');
            document.getElementById('hamburger').setAttribute('aria-expanded', 'false');
        }});
    }});
</script>
</body>
</html>"""


def build_card_html(meta, post_date):
    slug    = meta["slug"]
    title   = meta["title"]
    excerpt = meta["excerpt"]
    sp      = meta.get("service_page") or "home-repairs"
    tag     = sp.replace("-", " ").title()
    return f"""        <article class="blog-card">
            <span class="card-tag">{tag}</span>
            <h2 class="card-title"><a href="{slug}.html">{title}</a></h2>
            <p class="card-date">{post_date}</p>
            <p class="card-excerpt">{excerpt}</p>
            <a href="{slug}.html" class="card-link">Read More \u2192</a>
        </article>"""


# ── main ───────────────────────────────────────────────────────────────────────
def run(niche, n_posts=3):
    print(f"MAXX Pro Weekly Generator — {date.today()}")
    client = get_client()

    tmpdir = tempfile.mkdtemp(prefix="maxxpro_")
    try:
        print(f"Cloning {GITHUB_REPO}...")
        clone_repo(tmpdir)

        blog_dir         = os.path.join(tmpdir, "blog")
        os.makedirs(blog_dir, exist_ok=True)
        publish_log_path = os.path.join(tmpdir, "publish_log.json")

        published_context = extract_published_context(publish_log_path)
        print(published_context[:300])

        print(f"\nGenerating metadata for {n_posts} posts...")
        posts_meta = generate_metadata(client, niche, published_context, n=n_posts)
        print(f"Got {len(posts_meta)} ideas")

        log_entries = (json.load(open(publish_log_path))
                       if os.path.exists(publish_log_path) else [])
        new_cards = []
        post_date = date.today().strftime("%B %d, %Y")

        for meta in posts_meta:
            try:
                slug      = meta.get("slug") or slugify(meta["title"])
                meta["slug"] = slug
                print(f"\n  Generating: {meta['title']}")

                body_html = generate_post_body(client, meta, niche)
                post_html = build_post_html(meta, body_html, post_date)

                post_path = os.path.join(blog_dir, f"{slug}.html")
                with open(post_path, "w") as f:
                    f.write(post_html)
                print(f"  Written: blog/{slug}.html")

                new_cards.append(build_card_html(meta, post_date))

                log_entries.append({
                    "slug":  slug,
                    "title": meta["title"],
                    "topic": meta.get("topic", meta.get("keyword", "")),
                    "date":  str(date.today()),
                    "url":   f"{SITE_URL}/blog/{slug}.html",
                })

            except Exception as e:
                print(f"  ERROR on '{meta.get('title','?')}': {e}")
                continue

        # Inject new cards into blog/index.html
        index_path = os.path.join(blog_dir, "index.html")
        if os.path.exists(index_path) and new_cards:
            with open(index_path) as f:
                idx = f.read()
            insert = "\n".join(new_cards) + "\n        "
            idx = idx.replace("        <!-- POSTS_INJECT -->",
                              insert + "<!-- POSTS_INJECT -->")
            with open(index_path, "w") as f:
                f.write(idx)
            print(f"\n  Updated blog/index.html (+{len(new_cards)} cards)")

        # Save publish log
        with open(publish_log_path, "w") as f:
            json.dump(log_entries, f, indent=2)
        print(f"  publish_log.json: {len(log_entries)} total entries")

        # Always write last_run.json so we can confirm execution from GitHub
        last_run = {
            "run_at": str(date.today()),
            "posts_generated": len(new_cards),
            "status": "success",
            "errors": [],
        }
        with open(os.path.join(tmpdir, "last_run.json"), "w") as f:
            json.dump(last_run, f, indent=2)

        pushed = git_push(
            tmpdir,
            f"blog: add {len(new_cards)} post(s) [{date.today()}]"
        )
        if pushed:
            print(f"\nPushed to GitHub — Railway will redeploy automatically.")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAXX Pro weekly blog generator")
    parser.add_argument("--niche", default=BLOG_NICHE,
                        help="Blog niche description")
    parser.add_argument("--n", type=int, default=3,
                        help="Number of posts to generate")
    args = parser.parse_args()
    try:
        run(args.niche, args.n)
    except Exception as exc:
        import traceback
        print(f"FATAL: {exc}")
        traceback.print_exc()
        # Try to push an error log so we can see it on GitHub
        try:
            import tempfile as _tf, subprocess as _sp
            _td = _tf.mkdtemp(prefix="maxxpro_err_")
            _url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
            _sp.run(["git", "clone", "--depth=1", _url, _td], check=True,
                    capture_output=True)
            with open(os.path.join(_td, "last_run.json"), "w") as _f:
                json.dump({"run_at": str(date.today()), "status": "error",
                           "error": str(exc),
                           "traceback": traceback.format_exc()}, _f, indent=2)
            git_push(_td, f"blog: error log [{date.today()}]")
        except Exception:
            pass
        raise


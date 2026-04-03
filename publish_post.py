#!/usr/bin/env python3
"""
Single post publisher for MAXX Pro — used for manual/one-off posts.
Import generate_post_html() and generate_card_html() from this module,
or run directly to see usage.
"""
import os, re
from datetime import date

SITE_URL = "https://maxxprollc.com"


def slugify(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "-", text.lower())).strip("-")


def generate_post_html(slug, title, tag, excerpt, body_html, post_date):
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
        .post-title {{ font-family: var(--font-display); font-size: clamp(1.8rem,4vw,3rem); font-weight: 700; text-transform: uppercase; color: var(--chrome-hi); margin-bottom: 0.75rem; line-height: 1.15; }}
        .post-date {{ font-size: 0.8rem; color: var(--muted); margin-bottom: 2rem; }}
        .post-excerpt {{ font-size: 1.1rem; color: var(--chrome); font-weight: 300; margin-bottom: 2.5rem; padding-bottom: 2rem; border-bottom: 1px solid rgba(204,0,0,0.2); }}
        .post-body h2 {{ font-family: var(--font-display); font-size: clamp(1.3rem,2.5vw,1.9rem); font-weight: 700; text-transform: uppercase; color: var(--chrome-hi); margin: 2.5rem 0 1rem; }}
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


def generate_card_html(slug, title, tag, excerpt, post_date):
    return f"""        <article class="blog-card">
            <span class="card-tag">{tag}</span>
            <h2 class="card-title"><a href="{slug}.html">{title}</a></h2>
            <p class="card-date">{post_date}</p>
            <p class="card-excerpt">{excerpt}</p>
            <a href="{slug}.html" class="card-link">Read More \u2192</a>
        </article>"""


if __name__ == "__main__":
    print("publish_post.py — import generate_post_html() and generate_card_html()")
    print(f"SITE_URL: {SITE_URL}")

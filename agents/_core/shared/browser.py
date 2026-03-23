"""
AUROS AI — Playwright Browser Wrapper
Full JS-rendering scraper that replaces BeautifulSoup for modern websites.
Falls back to requests + BeautifulSoup if Playwright is not installed.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

# ---------------------------------------------------------------------------
# Playwright availability detection
# ---------------------------------------------------------------------------

_HAS_PLAYWRIGHT = False
try:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout
    _HAS_PLAYWRIGHT = True
except ImportError:
    pass

# Fallback imports (always available)
import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT = 20_000  # ms
_MAX_RETRIES = 2
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_SOCIAL_DOMAINS: dict[str, str] = {
    "instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "facebook.com": "facebook",
    "linkedin.com": "linkedin",
    "youtube.com": "youtube",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "threads.net": "threads",
    "pinterest.com": "pinterest",
    "vimeo.com": "vimeo",
    "behance.net": "behance",
    "dribbble.com": "dribbble",
}


# ═══════════════════════════════════════════════════════════════════════════
# Playwright-based scraper (primary)
# ═══════════════════════════════════════════════════════════════════════════

async def scrape_page(url: str, *, timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """
    Navigate to *url*, wait for JS rendering, and return structured page data.

    Returns dict with keys:
        url, html, text, title, meta_tags, headings, links, images,
        colors, fonts, social_links, error (if any).
    """
    if not _HAS_PLAYWRIGHT:
        return _scrape_fallback(url)

    result = _empty_result(url)

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=_USER_AGENT,
                    viewport={"width": 1440, "height": 900},
                    ignore_https_errors=True,
                )
                page = await context.new_page()

                await page.goto(url, wait_until="networkidle", timeout=timeout)

                # ── Core data ────────────────────────────────────────────
                result["html"] = await page.content()
                result["title"] = await page.title()
                result["text"] = await page.evaluate(
                    "() => document.body ? document.body.innerText : ''"
                )

                # ── Meta tags ────────────────────────────────────────────
                result["meta_tags"] = await page.evaluate("""() => {
                    const metas = {};
                    document.querySelectorAll('meta').forEach(m => {
                        const key = m.getAttribute('name')
                            || m.getAttribute('property')
                            || m.getAttribute('http-equiv');
                        if (key) metas[key] = m.getAttribute('content') || '';
                    });
                    return metas;
                }""")

                # ── Headings ─────────────────────────────────────────────
                result["headings"] = await page.evaluate("""() => {
                    const headings = [];
                    document.querySelectorAll('h1, h2, h3, h4').forEach(h => {
                        const text = h.innerText.trim();
                        if (text) headings.push({level: h.tagName.toLowerCase(), text: text.slice(0, 300)});
                    });
                    return headings;
                }""")

                # ── Links ────────────────────────────────────────────────
                result["links"] = await page.evaluate("""() => {
                    const links = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        links.push({href: a.href, text: (a.innerText || '').trim().slice(0, 120)});
                    });
                    return links.slice(0, 500);
                }""")

                # ── Images ───────────────────────────────────────────────
                result["images"] = await page.evaluate("""() => {
                    const imgs = [];
                    document.querySelectorAll('img').forEach(img => {
                        imgs.push({
                            src: img.src || img.getAttribute('data-src') || '',
                            alt: img.alt || '',
                            width: img.naturalWidth || 0,
                            height: img.naturalHeight || 0,
                        });
                    });
                    return imgs.slice(0, 200);
                }""")

                # ── Computed colors ───────────────────────────────────────
                result["colors"] = await page.evaluate("""() => {
                    const colorSet = new Set();
                    const sample = document.querySelectorAll(
                        'body, header, footer, nav, main, section, h1, h2, h3, a, button, p, span, div'
                    );
                    sample.forEach(el => {
                        const cs = getComputedStyle(el);
                        [cs.color, cs.backgroundColor, cs.borderColor].forEach(c => {
                            if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') colorSet.add(c);
                        });
                    });
                    return [...colorSet].slice(0, 60);
                }""")

                # ── Fonts ────────────────────────────────────────────────
                result["fonts"] = await page.evaluate("""() => {
                    const fontSet = new Set();
                    const sample = document.querySelectorAll('body, h1, h2, h3, p, a, button, span');
                    sample.forEach(el => {
                        const ff = getComputedStyle(el).fontFamily;
                        if (ff) fontSet.add(ff);
                    });
                    return [...fontSet].slice(0, 20);
                }""")

                # ── Social links ─────────────────────────────────────────
                result["social_links"] = _extract_socials_from_links(result["links"])

                await browser.close()
            return result

        except Exception as exc:
            if attempt >= _MAX_RETRIES:
                result["error"] = f"Playwright scrape failed after {_MAX_RETRIES} attempts: {exc}"
                print(f"[AUROS] Browser scrape failed: {url} — {exc}")
            else:
                await asyncio.sleep(1)

    return result


async def scrape_multiple(urls: list[str], *, timeout: int = _DEFAULT_TIMEOUT) -> list[dict]:
    """Scrape several URLs concurrently."""
    tasks = [scrape_page(u, timeout=timeout) for u in urls]
    return await asyncio.gather(*tasks)


async def screenshot_page(
    url: str,
    output_path: str,
    *,
    full_page: bool = True,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    """Take a screenshot of *url* and save to *output_path*. Returns the path."""
    if not _HAS_PLAYWRIGHT:
        raise RuntimeError(
            "Playwright is not installed. Run: pip install playwright && playwright install chromium"
        )

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout)
        except Exception:
            # Fall back to domcontentloaded if networkidle times out
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)

        await page.screenshot(path=output_path, full_page=full_page)
        await browser.close()

    return output_path


async def extract_social_links(url: str, *, timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """
    Scrape a page and return a mapping of platform -> profile URL.
    E.g. {"instagram": "https://instagram.com/handle", ...}
    """
    data = await scrape_page(url, timeout=timeout)
    return data.get("social_links", {})


# ═══════════════════════════════════════════════════════════════════════════
# Synchronous convenience wrapper
# ═══════════════════════════════════════════════════════════════════════════

def scrape_sync(url: str, *, timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Blocking wrapper around :func:`scrape_page` for non-async callers."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already inside an event loop — spin up a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, scrape_page(url, timeout=timeout)).result()

    return asyncio.run(scrape_page(url, timeout=timeout))


# ═══════════════════════════════════════════════════════════════════════════
# BeautifulSoup fallback
# ═══════════════════════════════════════════════════════════════════════════

def _scrape_fallback(url: str) -> dict:
    """Lightweight fallback when Playwright is not installed."""
    result = _empty_result(url)

    try:
        headers = {"User-Agent": _USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        result["html"] = resp.text
        result["title"] = soup.title.string.strip() if soup.title and soup.title.string else ""
        result["text"] = soup.get_text(separator=" ", strip=True)[:10_000]

        # Meta tags
        for meta in soup.find_all("meta"):
            key = meta.get("name") or meta.get("property") or meta.get("http-equiv")
            if key:
                result["meta_tags"][key] = meta.get("content", "")

        # Headings
        for tag in ("h1", "h2", "h3", "h4"):
            for el in soup.find_all(tag):
                text = el.get_text(strip=True)
                if text:
                    result["headings"].append({"level": tag, "text": text[:300]})

        # Links
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("http"):
                href = urljoin(url, href)
            result["links"].append({"href": href, "text": a.get_text(strip=True)[:120]})
        result["links"] = result["links"][:500]

        # Images
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if src and not src.startswith("http"):
                src = urljoin(url, src)
            result["images"].append({
                "src": src,
                "alt": img.get("alt", ""),
                "width": 0,
                "height": 0,
            })
        result["images"] = result["images"][:200]

        # Social links
        result["social_links"] = _extract_socials_from_links(result["links"])

        # Fonts — parse from CSS (best-effort)
        for style in soup.find_all("style"):
            text = style.string or ""
            families = re.findall(r"font-family\s*:\s*([^;}{]+)", text)
            for fam in families:
                result["fonts"].append(fam.strip().strip("'\""))
        result["fonts"] = list(set(result["fonts"]))[:20]

    except Exception as exc:
        result["error"] = f"Fallback scrape failed: {exc}"
        print(f"[AUROS] Fallback scrape failed: {url} — {exc}")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _empty_result(url: str) -> dict[str, Any]:
    return {
        "url": url,
        "html": "",
        "text": "",
        "title": "",
        "meta_tags": {},
        "headings": [],
        "links": [],
        "images": [],
        "colors": [],
        "fonts": [],
        "social_links": {},
        "error": None,
    }


def _extract_socials_from_links(links: list[dict]) -> dict[str, str]:
    """Given a list of {href, text} link dicts, return platform -> URL mapping."""
    socials: dict[str, str] = {}
    for link in links:
        href = link.get("href", "")
        for domain, platform in _SOCIAL_DOMAINS.items():
            if domain in href and platform not in socials:
                socials[platform] = href
                break
    return socials

"""
AUROS AI — Web & Social Scraper
Scrapes websites and researches social media presence using Tavily + BeautifulSoup.
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from agents.shared.config import TAVILY_API_KEY


def scrape_website(url: str) -> dict:
    """
    Scrape a website for marketing-relevant data:
    - Page title, meta description, headings
    - CTAs and conversion elements
    - Content structure and messaging
    """
    result = {
        "url": url,
        "title": "",
        "meta_description": "",
        "headings": [],
        "ctas": [],
        "content_summary": "",
        "images_count": 0,
        "links_count": 0,
        "has_blog": False,
        "has_contact_form": False,
        "social_links": [],
    }

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Title
        result["title"] = soup.title.string.strip() if soup.title else ""

        # Meta description
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            result["meta_description"] = meta.get("content", "")

        # Headings (h1-h3)
        for tag in ["h1", "h2", "h3"]:
            for heading in soup.find_all(tag):
                text = heading.get_text(strip=True)
                if text:
                    result["headings"].append({"level": tag, "text": text[:200]})

        # CTAs (buttons and links with action words)
        cta_keywords = ["book", "contact", "get started", "sign up", "buy", "order",
                        "schedule", "learn more", "free", "try", "demo", "call"]
        for el in soup.find_all(["a", "button"]):
            text = el.get_text(strip=True).lower()
            if any(kw in text for kw in cta_keywords):
                result["ctas"].append(el.get_text(strip=True)[:100])

        # Counts
        result["images_count"] = len(soup.find_all("img"))
        result["links_count"] = len(soup.find_all("a"))

        # Blog detection
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if "blog" in href or "news" in href or "articles" in href:
                result["has_blog"] = True
                break

        # Contact form detection
        if soup.find("form"):
            result["has_contact_form"] = True

        # Social links
        social_domains = ["instagram.com", "tiktok.com", "facebook.com",
                          "linkedin.com", "youtube.com", "twitter.com", "x.com"]
        for a in soup.find_all("a", href=True):
            href = a["href"]
            for domain in social_domains:
                if domain in href:
                    result["social_links"].append(href)
                    break

        # Get page text for content analysis (first 3000 chars)
        body_text = soup.get_text(separator=" ", strip=True)
        result["content_summary"] = body_text[:3000]

    except Exception as e:
        result["error"] = str(e)
        print(f"[AUROS] Website scrape failed: {url} — {e}")

    return result


def research_social_presence(company: str, socials: dict[str, str]) -> list[dict]:
    """
    Research a company's social media presence using Tavily.
    Since we can't directly scrape most social platforms (auth walls),
    we use search to find public info about their social activity.
    """
    client = TavilyClient(api_key=TAVILY_API_KEY)
    results = []

    platform_queries = {
        "instagram": [
            f"{company} instagram marketing content",
            f"site:instagram.com {socials.get('instagram', company)}",
        ],
        "tiktok": [
            f"{company} tiktok content marketing",
            f"site:tiktok.com {socials.get('tiktok', company)}",
        ],
        "facebook": [
            f"{company} facebook page marketing",
        ],
        "linkedin": [
            f"{company} linkedin company page posts",
        ],
        "youtube": [
            f"{company} youtube channel marketing videos",
        ],
        "twitter": [
            f"{company} twitter X social media presence",
        ],
    }

    for platform, handle in socials.items():
        queries = platform_queries.get(platform, [f"{company} {platform}"])
        platform_data = {
            "platform": platform.title(),
            "handle": handle,
            "research": [],
        }

        for query in queries:
            try:
                response = client.search(
                    query=query,
                    search_depth="basic",
                    max_results=5,
                    days=30,
                )
                for r in response.get("results", []):
                    platform_data["research"].append({
                        "title": r.get("title", ""),
                        "content": r.get("content", "")[:500],
                        "url": r.get("url", ""),
                    })
            except Exception as e:
                print(f"[AUROS] Social research failed: {platform} — {e}")

        results.append(platform_data)
        print(f"[AUROS] {platform.title()}: {len(platform_data['research'])} results")

    return results

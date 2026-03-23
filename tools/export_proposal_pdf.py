#!/usr/bin/env python3
"""
AUROS AI — Export enhanced proposal to PDF + take verification screenshots.
Uses Playwright for high-fidelity rendering.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLIENT_DIR = PROJECT_ROOT / "portfolio" / "client_the_imagine_team"
HTML_PATH = CLIENT_DIR / "04_deliverables" / "proposal_the_imagine_team_enhanced.html"
PDF_PATH = CLIENT_DIR / "04_deliverables" / "proposal_the_imagine_team_2026.pdf"
SCREENSHOT_PATH = CLIENT_DIR / "04_deliverables" / "proposal_preview.png"


async def export():
    from playwright.async_api import async_playwright

    print("[AUROS] Starting Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        # Load the HTML file
        file_url = f"file://{HTML_PATH}"
        print(f"[AUROS] Loading {file_url}")
        await page.goto(file_url, wait_until="networkidle")

        # Wait for fonts to load
        await page.wait_for_timeout(2000)

        # Force all scroll animations to be visible (for PDF)
        await page.evaluate("""
            document.querySelectorAll('.animate-on-scroll').forEach(el => {
                el.classList.add('visible');
            });
        """)

        # Take full-page screenshot for verification
        print("[AUROS] Taking verification screenshot...")
        await page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
        screenshot_size = SCREENSHOT_PATH.stat().st_size / 1024 / 1024
        print(f"  Screenshot saved: {SCREENSHOT_PATH.name} ({screenshot_size:.1f} MB)")

        # Export to PDF
        print("[AUROS] Exporting PDF...")
        await page.pdf(
            path=str(PDF_PATH),
            format="A4",
            landscape=True,
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )

        pdf_size = PDF_PATH.stat().st_size / 1024 / 1024
        print(f"  PDF saved: {PDF_PATH.name} ({pdf_size:.1f} MB)")

        # Take section screenshots for verification
        print("\n[AUROS] Taking section screenshots for verification...")
        sections = [
            ("cover", "section.cover"),
            ("cabinet_hero", "#cabinet .campaign-hero"),
            ("cabinet_gallery", "#cabinet .campaign-gallery"),
            ("titanic_hero", "#titanic .campaign-hero"),
            ("trolls_hero", "#trolls .campaign-hero"),
            ("bundle", "#bundle"),
        ]

        verify_dir = CLIENT_DIR / "04_deliverables" / "preview_sections"
        verify_dir.mkdir(exist_ok=True)

        for name, selector in sections:
            try:
                el = await page.query_selector(selector)
                if el:
                    await el.screenshot(path=str(verify_dir / f"{name}.png"))
                    print(f"  OK: {name}")
                else:
                    print(f"  SKIP: {name} (selector not found)")
            except Exception as e:
                print(f"  SKIP: {name} ({e})")

        await browser.close()

    print(f"\n[AUROS] Export complete!")
    print(f"  HTML: {HTML_PATH}")
    print(f"  PDF:  {PDF_PATH}")
    print(f"  Verification screenshots: {verify_dir}")


if __name__ == "__main__":
    asyncio.run(export())

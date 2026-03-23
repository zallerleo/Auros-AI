#!/usr/bin/env python3
"""
AUROS AI — Scrape and process images for the enhanced proposal.
Downloads exhibition images, resizes, compresses, and saves to media/proposal_ready/.
"""

from __future__ import annotations

import json
import io
import sys
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEDIA_DIR = PROJECT_ROOT / "portfolio" / "client_the_imagine_team" / "media"
OUTPUT_DIR = MEDIA_DIR / "proposal_ready"


def download_image(url: str, timeout: int = 15) -> Image.Image | None:
    """Download an image from URL and return as PIL Image."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        return Image.open(io.BytesIO(data))
    except Exception as e:
        print(f"  SKIP: {url[:80]}... — {e}")
        return None


def process_image(img: Image.Image, max_width: int = 1200, quality: int = 80) -> bytes:
    """Resize and compress image to JPEG bytes."""
    # Convert to RGB if necessary (handles PNG with alpha, etc.)
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (11, 15, 26))  # midnight background
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if wider than max
    if img.width > max_width:
        ratio = max_width / img.width
        new_h = int(img.height * ratio)
        img = img.resize((max_width, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def save_image(data: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    size_kb = len(data) / 1024
    print(f"  SAVED: {path.name} ({size_kb:.0f} KB)")


def process_local_images():
    """Process already-downloaded images."""
    print("\n=== Processing local images ===")

    # Titanic — already have JPGs
    titanic_dir = OUTPUT_DIR / "titanic"
    src_dir = MEDIA_DIR / "titanic" / "downloaded"
    if src_dir.exists():
        for i, f in enumerate(sorted(src_dir.glob("*.jpg"))[:5]):
            img = Image.open(f)
            data = process_image(img, max_width=1200)
            save_image(data, titanic_dir / f"titanic_{i+1:02d}.jpg")

    # Dambo — have JPGs and PNGs
    dambo_dir = OUTPUT_DIR / "dambo"
    src_dir = MEDIA_DIR / "dambo" / "downloaded"
    if src_dir.exists():
        for i, f in enumerate(sorted(src_dir.glob("*.*"))[:5]):
            if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                img = Image.open(f)
                data = process_image(img, max_width=1200)
                save_image(data, dambo_dir / f"dambo_local_{i+1:02d}.jpg")


def scrape_cabinet():
    """Download Cabinet of Curiosities images from thecabinetlv.com."""
    print("\n=== Scraping Cabinet of Curiosities ===")
    out_dir = OUTPUT_DIR / "cabinet"

    urls = [
        ("cabinet_hero_left.jpg", "https://thecabinetlv.com/wp-content/uploads/2026/01/The-Cabinet-and-The-Lock-Left-scaled.jpg"),
        ("cabinet_hero_mid.jpg", "https://thecabinetlv.com/wp-content/uploads/2026/01/The-Cabinet-and-The-Lock-Middle-scaled.jpg"),
        ("cabinet_hero_right.jpg", "https://thecabinetlv.com/wp-content/uploads/2026/01/The-Cabinet-and-The-Lock-Right-scaled.jpg"),
        ("cabinet_promo_1.jpg", "https://thecabinetlv.com/wp-content/uploads/2024/06/The-Cabinet-promo-1-683x1024.jpg"),
        ("cabinet_promo_2.jpg", "https://thecabinetlv.com/wp-content/uploads/2024/06/The-Cabinet-promo-2-683x1024.jpg"),
        ("cabinet_directions.jpg", "https://thecabinetlv.com/wp-content/uploads/2023/10/walking-directions.jpg"),
        ("cabinet_lock_interior.jpg", "https://thelocklv.com/wp-content/uploads/2023/01/DSC07078-sm.jpg"),
        ("cabinet_happy_hour.png", "https://thecabinetlv.com/wp-content/uploads/2024/09/CabinetLock_TableTent_HappyHour.png"),
    ]

    for fname, url in urls:
        print(f"  Downloading {fname}...")
        img = download_image(url)
        if img:
            data = process_image(img, max_width=1200)
            save_image(data, out_dir / fname)


def scrape_titanic():
    """Download Titanic exhibition images from Wix CDN."""
    print("\n=== Scraping Titanic Exhibition ===")
    out_dir = OUTPUT_DIR / "titanic"

    # Modify Wix URLs: use w_1200, remove enc_avif, use quality_auto
    wix_images = [
        ("titanic_grand_staircase.jpg", "https://static.wixstatic.com/media/339af9_025e260be82a41f08a6499d84a59ca13~mv2.jpg/v1/fit/w_1200,h_749,q_90/339af9_025e260be82a41f08a6499d84a59ca13~mv2.jpg"),
        ("titanic_hall_1.jpg", "https://static.wixstatic.com/media/339af9_3f667e573905489384a9c8023750b6bb~mv2.jpg/v1/fit/w_1200,h_749,q_90/339af9_3f667e573905489384a9c8023750b6bb~mv2.jpg"),
        ("titanic_hall_2.jpg", "https://static.wixstatic.com/media/339af9_743378f62b3e43b98eca4157aae6401d~mv2.jpg/v1/fit/w_1200,h_749,q_90/339af9_743378f62b3e43b98eca4157aae6401d~mv2.jpg"),
        ("titanic_atmosphere_1.jpg", "https://static.wixstatic.com/media/339af9_a0b04b0452d2468bb8b2a8c3ed31d8a4~mv2.jpg/v1/fit/w_1200,h_749,q_90/339af9_a0b04b0452d2468bb8b2a8c3ed31d8a4~mv2.jpg"),
        ("titanic_atmosphere_2.jpg", "https://static.wixstatic.com/media/339af9_bb2ae02ec959423ab728d396607c32ba~mv2.jpg/v1/fit/w_1200,h_749,q_90/339af9_bb2ae02ec959423ab728d396607c32ba~mv2.jpg"),
        ("titanic_imagine_1.jpg", "https://static.wixstatic.com/media/23103f_01149aef6c94468189969219946716da~mv2.jpeg/v1/fit/w_1200,h_599,q_90/23103f_01149aef6c94468189969219946716da~mv2.jpeg"),
        ("titanic_imagine_2.jpg", "https://static.wixstatic.com/media/23103f_e0058fdc9639439b8befcb18c9050650~mv2.jpeg/v1/fit/w_1200,h_749,q_90/23103f_e0058fdc9639439b8befcb18c9050650~mv2.jpeg"),
    ]

    for fname, url in wix_images:
        print(f"  Downloading {fname}...")
        img = download_image(url)
        if img:
            data = process_image(img, max_width=1200)
            save_image(data, out_dir / fname)


def scrape_dambo():
    """Download Thomas Dambo troll sculpture images."""
    print("\n=== Scraping Thomas Dambo Trolls ===")
    out_dir = OUTPUT_DIR / "dambo"

    # Cherry-pick the most visually striking sculptures
    dambo_images = [
        ("dambo_giants_tour.jpg", "https://www.thomasdambo.com/data/asset/01eqcy/w1200/671b5bbaa61dfc1e1b037e37_153_2024_helle-haltben_giants-legends-tour.png"),
        ("dambo_golden_rabbit.jpg", "https://www.thomasdambo.com/data/asset/qna30s/w1200/6673f3abcad237f83a9d2c29_the-golden-rabbit-small-copy-p-2000.jpg"),
        ("dambo_barefoot_frida.jpg", "https://www.thomasdambo.com/data/asset/g3acky/w1200/667aa0a7cb23f93ad52f5425_barefoot-frida-small-copy-p-2000.jpg"),
        ("dambo_trollercoaster.jpg", "https://www.thomasdambo.com/data/asset/rxn1os/w1200/6683ba2ba20109e931eac45b_trollercoasterfire.jpg"),
        ("dambo_oscar_bird_king.jpg", "https://www.thomasdambo.com/data/asset/gso7xb/w1200/65c209419f9837785e93ee3e_10-oscar-the-bird-king-vashon-island-washington-scaled.jpg"),
        ("dambo_pia_peacekeeper.jpg", "https://www.thomasdambo.com/data/asset/fualb5/w1200/65c0e523543a20aef1a76b7e_06-pia-the-peace-keeper-bainbridge-island-wa.jpg"),
        ("dambo_rita_rock.jpg", "https://www.thomasdambo.com/data/asset/c7mght/w1200/65c0e0a85c7bfabaf109c066_04-rita-the-rock-planter-cripple-creek-victor-colorado-scaled.jpg"),
        ("dambo_save_humans.jpg", "https://www.thomasdambo.com/data/asset/gfem8x/w1200/65dddb9bfd1b364f094055b1_save-the-humans-cover-riddle.jpg"),
        ("dambo_malins_fountain.jpg", "https://www.thomasdambo.com/data/asset/4dk0zn/w1200/660e94c02fd0ab1cbdb2c295_malins-fountain-for-website.jpg"),
        ("dambo_explorers_sentosa.jpg", "https://www.thomasdambo.com/data/asset/5ewkq4/w1200/65cc81dc93d710b7656e540b_106_2023_little-lyn_explorers-of-sentosa_web.jpg"),
    ]

    for fname, url in dambo_images:
        print(f"  Downloading {fname}...")
        img = download_image(url)
        if img:
            data = process_image(img, max_width=1200)
            save_image(data, out_dir / fname)


def main():
    print("AUROS AI — Proposal Image Scraper")
    print(f"Output: {OUTPUT_DIR}")

    # Clean output dir
    if OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    process_local_images()
    scrape_cabinet()
    scrape_titanic()
    scrape_dambo()

    # Summary
    print("\n=== SUMMARY ===")
    total = 0
    total_size = 0
    for d in sorted(OUTPUT_DIR.iterdir()):
        if d.is_dir():
            files = list(d.glob("*.jpg"))
            size = sum(f.stat().st_size for f in files) / 1024
            print(f"  {d.name}: {len(files)} images, {size:.0f} KB")
            total += len(files)
            total_size += size
    print(f"  TOTAL: {total} images, {total_size:.0f} KB ({total_size/1024:.1f} MB)")


if __name__ == "__main__":
    main()

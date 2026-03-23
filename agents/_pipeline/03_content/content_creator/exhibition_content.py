#!/usr/bin/env python3
"""
AUROS AI — Exhibition Content Creator
Generates ticket-selling content for specific exhibitions.
Cinematic, FOMO-driven, experience-focused marketing.

Usage:
    python -m agents.content_creator.exhibition_content --company "The Imagine Team"
"""

from __future__ import annotations

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR
from agents.shared.llm import generate


def _load_knowledge() -> str:
    try:
        from agents.shared.knowledge import get_frameworks_summary
        return get_frameworks_summary(["copywriting", "psychology", "video_marketing"])
    except Exception:
        return ""


# ─── EXHIBITION DATA ───

EXHIBITIONS = [
    {
        "name": "Harry Potter: The Exhibition",
        "slug": "harry_potter",
        "tagline": "Step inside the wizarding world",
        "description": "The most comprehensive touring exhibition about Harry Potter film-making magic, including Fantastic Beasts and Cursed Child elements. Immersive environments, authentic props, costumes, and magical creatures.",
        "audience": "Families, millennials, Gen Z, Harry Potter fans, pop culture enthusiasts",
        "emotional_hooks": ["nostalgia", "childhood magic", "belonging to a world", "wonder", "FOMO"],
        "visual_keywords": ["golden light through castle windows", "wands and spells", "Hogwarts Great Hall", "magical creatures", "robes and sorting hat", "Diagon Alley"],
        "instagram": "@harrypotter_exhibition",
        "tone": "Magical, inviting, wonder-filled, slightly mysterious",
    },
    {
        "name": "Titanic: The Exhibition",
        "slug": "titanic",
        "tagline": "Experience history like never before",
        "description": "Over 300 artifacts from Titanic and her sister ships. Vividly brings to life the dramatic story of the most famous ship ever built — the luxury, the people, the tragedy, the legacy.",
        "audience": "History enthusiasts, families, educators, tourists, 25-65 age range",
        "emotional_hooks": ["awe at scale", "human stories", "tragedy and beauty", "time travel", "respect"],
        "visual_keywords": ["grand staircase", "ship hull at night", "period costumes", "artifacts under glass", "ocean depth", "opulent interiors"],
        "instagram": "@titanicexhibition",
        "tone": "Cinematic, reverent, dramatic, emotionally powerful",
    },
    {
        "name": "Imagine Van Gogh",
        "slug": "van_gogh",
        "tagline": "Step inside the paintings",
        "description": "An immersive experience deep inside Van Gogh's iconic paintings from his last years. Over 200 works of art projected in massive scale, surrounded by classical music. Walk through Starry Night.",
        "audience": "Art lovers, date night couples, Instagram-savvy millennials, culture seekers",
        "emotional_hooks": ["beauty overload", "Instagrammable moments", "art as experience", "emotional depth", "sensory immersion"],
        "visual_keywords": ["Starry Night projected on walls", "sunflower fields wrapping around you", "swirling colors at massive scale", "silhouettes in light", "brushstrokes you can walk through"],
        "instagram": "@imaginevangogh",
        "tone": "Poetic, breathtaking, intimate yet grand, visually intoxicating",
    },
    {
        "name": "Ice Dinosaurs",
        "slug": "ice_dinosaurs",
        "tagline": "Discover the frozen giants",
        "description": "Newly discovered Arctic-dwelling dinosaurs never-before-seen in an exhibition. Built around groundbreaking paleontological discoveries that expand our understanding of dinosaur physiology and migration.",
        "audience": "Families with kids 4-14, science enthusiasts, educators, school groups",
        "emotional_hooks": ["discovery", "wow factor", "kid excitement", "new science", "adventure"],
        "visual_keywords": ["massive dinosaur in ice cave", "frozen tundra environment", "kid looking up at giant skeleton", "aurora borealis backdrop", "interactive dig site"],
        "instagram": "@theimagineteam",
        "tone": "Exciting, adventurous, awe-inspiring, educational but fun",
    },
]


# ─── VIDEO AD SCRIPTS (EXHIBITION-SPECIFIC) ───

VIDEO_PROMPT = """You are an elite creative director making ads that SELL TICKETS to exhibitions.
Your ads should feel like MOVIE TRAILERS — cinematic, emotional, impossible to scroll past.

The current marketing for these exhibitions is boring and generic. We need content that makes people
feel like they'll deeply regret not going. Every frame should sell the EXPERIENCE, not the company.

EXHIBITION:
{exhibition_data}

MARKETING KNOWLEDGE:
{knowledge}

Generate 3 video ad scripts:

**SCRIPT 1: 15-SECOND REEL (TikTok / Instagram Reels)**
Structure: HOOK → WOW MOMENT → URGENCY CTA
- 0-2s: Pattern interrupt that stops the scroll (text overlay + dramatic visual)
- 2-10s: The single most jaw-dropping moment of the exhibition
- 10-15s: Urgency CTA ("Tickets selling fast" / "Limited run" / "Don't miss this")
Music: Trending audio style, dramatic build

**SCRIPT 2: 30-SECOND AD (Instagram / YouTube)**
Structure: FOMO OPEN → EXPERIENCE MONTAGE → SOCIAL PROOF → CTA
- 0-3s: Open with something that creates instant FOMO ("POV: You just walked into...")
- 3-18s: Rapid-cut montage of 5 most visually stunning moments (each 3s)
- 18-25s: Reactions — real people being amazed, kids' faces lighting up, couples in awe
- 25-30s: "Book now" CTA with location/date urgency

**SCRIPT 3: 60-SECOND CINEMATIC (YouTube / Facebook)**
Structure: Three-Act movie trailer style
- 0-5s: Dramatic hook — black screen with text, then REVEAL
- 5-20s: Act 1 — Build the world (slow, atmospheric, pull viewers IN)
- 20-40s: Act 2 — The experience explodes (faster cuts, bigger moments, emotional peaks)
- 40-52s: Act 3 — Human reaction + transformation ("I've never seen anything like this")
- 52-60s: Logo + CTA + urgency ("Now open. Tickets at [link]")

For EACH shot include:
- Exact timestamp
- Visual description (specific enough to generate with AI image/video tools)
- Text overlay (exact words on screen, big bold text for silent viewing)
- Voiceover OR music cue
- Camera motion (slow zoom, orbit, whip pan, drone shot, handheld)
- Transition to next shot

Return valid JSON:
{{
  "exhibition": "{exhibition_name}",
  "scripts": [
    {{
      "id": "15s_reel",
      "duration": 15,
      "title": "...",
      "concept": "One-line creative concept",
      "platform": "TikTok / Instagram Reels",
      "shots": [
        {{
          "shot_number": 1,
          "timestamp": "0:00 - 0:02",
          "visual": "Detailed AI generation prompt for this frame",
          "text_overlay": "Bold text shown on screen",
          "audio": "Music cue or voiceover",
          "camera": "Movement type",
          "transition": "Cut type to next shot"
        }}
      ],
      "music": {{
        "style": "...",
        "tempo_bpm": 0,
        "build": "How the music progresses",
        "reference_track": "Similar to..."
      }},
      "caption": "Full Instagram/TikTok caption with hashtags",
      "cta": "Exact call to action"
    }}
  ]
}}"""


# ─── SOCIAL MEDIA POSTS (EXHIBITION-SPECIFIC) ───

SOCIAL_PROMPT = """You are AUROS's social media specialist. Create 10 TICKET-SELLING social posts for this exhibition.

Every post exists for ONE reason: get people to buy tickets. No brand awareness fluff.
The current marketing is boring — we need posts that make people tag friends and say "WE HAVE TO GO."

EXHIBITION:
{exhibition_data}

MARKETING KNOWLEDGE:
{knowledge}

Generate 10 posts:
- 3x Instagram Carousel posts (5 slides each — hook slide → experience slides → CTA slide)
- 3x Instagram Reel concepts (hook + script outline + trending audio suggestion)
- 2x Instagram Stories (poll/quiz that drives engagement + swipe-up CTA)
- 2x TikTok concepts (POV / "Wait for it" / reaction style)

Every post MUST:
- Open with a hook that creates FOMO or curiosity (not "Check out our exhibition!")
- Show the EXPERIENCE, not the company
- Include a ticket-driving CTA
- Have specific visual direction for image/video generation
- Use the psychological trigger noted

BAD example: "Come visit our amazing exhibition! #exhibition #fun"
GOOD example: "POV: You just walked into a room where Starry Night surrounds you from floor to ceiling and you forgot how to breathe"

Return valid JSON:
{{
  "exhibition": "{exhibition_name}",
  "posts": [
    {{
      "id": 1,
      "platform": "instagram_carousel",
      "hook": "First line / first slide text",
      "slides": ["Slide 1 text", "Slide 2...", "Slide 5 CTA"],
      "caption": "Full caption",
      "visual_direction": "What each slide should look like",
      "hashtags": ["..."],
      "psychological_trigger": "FOMO / curiosity / social proof / etc",
      "posting_time": "Best time to post",
      "cta": "Get tickets link"
    }}
  ]
}}"""


# ─── HOOKS BANK (EXHIBITION-SPECIFIC) ───

HOOKS_PROMPT = """Create 15 scroll-stopping hooks for this exhibition. These hooks need to make people
STOP SCROLLING and feel like they're missing out if they don't go.

EXHIBITION:
{exhibition_data}

Types (3 each):
- POV hooks ("POV: you just...")
- "Wait for it" hooks (build anticipation)
- Reaction hooks ("Their face when they saw...")
- Challenge/question hooks ("Can you walk through Starry Night without crying?")
- FOMO hooks ("This closes in 2 weeks and you still haven't been")

Return valid JSON:
{{
  "exhibition": "{exhibition_name}",
  "hooks": [
    {{
      "id": 1,
      "type": "pov",
      "hook_text": "...",
      "visual_opener": "What the first frame looks like",
      "psychological_trigger": "...",
      "best_platform": "tiktok / reels / both"
    }}
  ]
}}"""


def generate_exhibition_content(company: str) -> dict:
    """Generate ticket-selling content for all exhibitions."""
    today = datetime.now().strftime("%Y-%m-%d")
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"
    content_dir = client_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    knowledge = _load_knowledge()[:3000]
    all_results = {}

    for exhibition in EXHIBITIONS:
        exhibit_name = exhibition["name"]
        exhibit_slug = exhibition["slug"]
        exhibit_dir = content_dir / exhibit_slug
        exhibit_dir.mkdir(parents=True, exist_ok=True)

        exhibition_data = json.dumps(exhibition, indent=2)

        print(f"\n[AUROS] ═══ {exhibit_name} ═══")

        # 1. Video Scripts
        print(f"[AUROS] Generating video scripts for {exhibit_name}...")
        prompt = VIDEO_PROMPT.format(
            exhibition_data=exhibition_data,
            knowledge=knowledge,
            exhibition_name=exhibit_name,
        )
        raw = generate(prompt, temperature=0.7, max_tokens=6000)
        json_str = raw.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[1]
            json_str = json_str.rsplit("```", 1)[0]
        try:
            scripts = json.loads(json_str)
        except json.JSONDecodeError:
            # Try repair
            repair = json_str.rstrip()
            for ch in ['"', '}', ']', '}', ']', '}']:
                try:
                    scripts = json.loads(repair)
                    break
                except json.JSONDecodeError:
                    repair += ch
            else:
                scripts = {"exhibition": exhibit_name, "scripts": [], "error": "JSON parse failed"}

        (exhibit_dir / f"video_scripts_{today}.json").write_text(json.dumps(scripts, indent=2))
        print(f"[AUROS] Video scripts saved — {len(scripts.get('scripts', []))} scripts")

        # 2. Social Posts
        print(f"[AUROS] Generating social posts for {exhibit_name}...")
        prompt = SOCIAL_PROMPT.format(
            exhibition_data=exhibition_data,
            knowledge=knowledge,
            exhibition_name=exhibit_name,
        )
        raw = generate(prompt, temperature=0.7, max_tokens=6000)
        json_str = raw.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[1]
            json_str = json_str.rsplit("```", 1)[0]
        try:
            posts = json.loads(json_str)
        except json.JSONDecodeError:
            repair = json_str.rstrip()
            for ch in ['"', '}', ']', '}', ']', '}']:
                try:
                    posts = json.loads(repair)
                    break
                except json.JSONDecodeError:
                    repair += ch
            else:
                posts = {"exhibition": exhibit_name, "posts": [], "error": "JSON parse failed"}

        (exhibit_dir / f"social_posts_{today}.json").write_text(json.dumps(posts, indent=2))
        print(f"[AUROS] Social posts saved — {len(posts.get('posts', []))} posts")

        # 3. Hooks
        print(f"[AUROS] Generating hooks for {exhibit_name}...")
        prompt = HOOKS_PROMPT.format(
            exhibition_data=exhibition_data,
            exhibition_name=exhibit_name,
        )
        raw = generate(prompt, temperature=0.8, max_tokens=3000)
        json_str = raw.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[1]
            json_str = json_str.rsplit("```", 1)[0]
        try:
            hooks = json.loads(json_str)
        except json.JSONDecodeError:
            hooks = {"exhibition": exhibit_name, "hooks": [], "error": "JSON parse failed"}

        (exhibit_dir / f"hooks_{today}.json").write_text(json.dumps(hooks, indent=2))
        print(f"[AUROS] Hooks saved — {len(hooks.get('hooks', []))} hooks")

        all_results[exhibit_slug] = {
            "scripts": scripts,
            "posts": posts,
            "hooks": hooks,
        }

    # Generate master production brief
    print("\n[AUROS] Building master production brief...")
    _render_exhibition_brief(company, all_results, content_dir, today)

    # Summary
    total_scripts = sum(len(r["scripts"].get("scripts", [])) for r in all_results.values())
    total_posts = sum(len(r["posts"].get("posts", [])) for r in all_results.values())
    total_hooks = sum(len(r["hooks"].get("hooks", [])) for r in all_results.values())
    print(f"\n[AUROS] ═══ CONTENT PRODUCTION COMPLETE ═══")
    print(f"[AUROS] {len(EXHIBITIONS)} exhibitions")
    print(f"[AUROS] {total_scripts} video scripts")
    print(f"[AUROS] {total_posts} social posts")
    print(f"[AUROS] {total_hooks} hooks")
    print(f"[AUROS] All saved to {content_dir}")

    return all_results


def _render_exhibition_brief(
    company: str,
    all_results: dict,
    content_dir: Path,
    today: str,
) -> None:
    """Render master production brief as HTML."""
    sections_html = ""

    for slug, data in all_results.items():
        exhibit_info = next((e for e in EXHIBITIONS if e["slug"] == slug), {})
        exhibit_name = exhibit_info.get("name", slug)

        # Scripts
        scripts_html = ""
        for script in data["scripts"].get("scripts", []):
            shots_html = ""
            for shot in script.get("shots", []):
                text_overlay = shot.get("text_overlay", "")
                shots_html += f"""
                <div class="shot">
                  <div class="shot-time">{shot.get('timestamp', '')}</div>
                  <div class="shot-body">
                    <div class="shot-visual">{shot.get('visual', '')}</div>
                    {f'<div class="shot-overlay">"{text_overlay}"</div>' if text_overlay else ''}
                    <div class="shot-tech">{shot.get('camera', '')} &middot; {shot.get('transition', '')}</div>
                  </div>
                </div>"""

            scripts_html += f"""
            <div class="script-block">
              <div class="script-title">{script.get('title', script.get('id', ''))}</div>
              <div class="script-badges">
                <span class="tag">{script.get('duration', '')}s</span>
                <span class="tag">{script.get('platform', '')}</span>
              </div>
              {f'<div class="concept">{script.get("concept", "")}</div>' if script.get("concept") else ''}
              <div class="shots-list">{shots_html}</div>
            </div>"""

        # Posts
        posts_html = ""
        for post in data["posts"].get("posts", [])[:5]:
            posts_html += f"""
            <div class="post-block">
              <span class="tag">{post.get('platform', '').replace('_', ' ').title()}</span>
              <span class="tag trigger">{post.get('psychological_trigger', '')}</span>
              <div class="post-hook">"{post.get('hook', '')}"</div>
              <div class="post-caption">{post.get('caption', '')[:250]}</div>
              <div class="post-visual">{post.get('visual_direction', '')[:200]}</div>
            </div>"""

        # Hooks
        hooks_html = ""
        for hook in data["hooks"].get("hooks", []):
            hooks_html += f"""
            <div class="hook-chip">
              <span class="hook-type">{hook.get('type', '').upper()}</span>
              "{hook.get('hook_text', '')}"
            </div>"""

        sections_html += f"""
        <div class="exhibit-section">
          <div class="exhibit-header">
            <h2>{exhibit_name}</h2>
            <p>{exhibit_info.get('tagline', '')}</p>
          </div>

          <h3>Video Scripts</h3>
          {scripts_html}

          <h3>Social Posts (top 5)</h3>
          <div class="posts-grid">{posts_html}</div>

          <h3>Hooks Bank</h3>
          <div class="hooks-list">{hooks_html}</div>
        </div>"""

    total_scripts = sum(len(r["scripts"].get("scripts", [])) for r in all_results.values())
    total_posts = sum(len(r["posts"].get("posts", [])) for r in all_results.values())
    total_hooks = sum(len(r["hooks"].get("hooks", [])) for r in all_results.values())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUROS — Exhibition Content Production Brief</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Inter', sans-serif; background: #0B0F1A; color: #FAFAF8; line-height: 1.6; }}

  .hero {{
    padding: 60px 48px;
    background: linear-gradient(135deg, #0B0F1A 0%, #1a1020 50%, #0B0F1A 100%);
    border-bottom: 2px solid rgba(201,168,76,0.2);
    text-align: center;
  }}
  .hero h1 {{ font-size: 42px; font-weight: 900; color: #C9A84C; letter-spacing: -2px; text-shadow: 0 0 40px rgba(201,168,76,0.3); }}
  .hero .sub {{ color: #6B7280; font-size: 14px; letter-spacing: 3px; text-transform: uppercase; margin-top: 8px; }}
  .hero .stats {{ display: flex; justify-content: center; gap: 48px; margin-top: 32px; }}
  .hero .stat {{ text-align: center; }}
  .hero .stat-num {{ font-size: 40px; font-weight: 900; color: #C9A84C; }}
  .hero .stat-lbl {{ font-size: 10px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; color: #6B7280; margin-top: 4px; }}

  .exhibit-section {{
    padding: 48px;
    border-bottom: 1px solid rgba(201,168,76,0.1);
  }}
  .exhibit-header {{
    margin-bottom: 32px;
    padding-bottom: 20px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }}
  .exhibit-header h2 {{
    font-size: 28px;
    font-weight: 900;
    color: #FAFAF8;
    letter-spacing: -1px;
  }}
  .exhibit-header p {{ color: #C9A84C; font-size: 14px; font-weight: 600; margin-top: 4px; }}

  h3 {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #8B6E2A;
    margin: 28px 0 16px;
  }}

  .tag {{
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    background: rgba(255,255,255,0.05);
    color: #9CA3AF;
    margin-right: 6px;
    margin-bottom: 6px;
  }}
  .tag.trigger {{ background: rgba(201,168,76,0.1); color: #C9A84C; }}

  .script-block {{
    background: #111827;
    border: 1px solid rgba(201,168,76,0.08);
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 16px;
  }}
  .script-title {{ font-size: 18px; font-weight: 800; margin-bottom: 8px; }}
  .script-badges {{ margin-bottom: 12px; }}
  .concept {{ font-size: 14px; color: #E8C96A; font-style: italic; margin-bottom: 16px; }}

  .shots-list {{ border-left: 2px solid rgba(201,168,76,0.15); padding-left: 20px; }}
  .shot {{ display: flex; gap: 14px; margin-bottom: 16px; }}
  .shot-time {{ font-size: 12px; font-weight: 700; color: #C9A84C; min-width: 80px; flex-shrink: 0; }}
  .shot-visual {{ font-size: 13px; color: #d4d4d4; }}
  .shot-overlay {{ font-size: 14px; font-weight: 800; color: #E8C96A; margin-top: 6px; }}
  .shot-tech {{ font-size: 11px; color: #4B5563; margin-top: 4px; }}

  .posts-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }}
  .post-block {{
    background: #111827;
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 20px;
  }}
  .post-hook {{ font-size: 16px; font-weight: 800; color: #FAFAF8; margin: 10px 0; line-height: 1.4; }}
  .post-caption {{ font-size: 12px; color: #9CA3AF; white-space: pre-line; margin-bottom: 10px; }}
  .post-visual {{ font-size: 11px; color: #4B5563; font-style: italic; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.04); }}

  .hooks-list {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .hook-chip {{
    background: #111827;
    border: 1px solid rgba(201,168,76,0.08);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 13px;
    color: #d4d4d4;
    flex: 1 1 300px;
    line-height: 1.4;
  }}
  .hook-type {{
    display: inline-block;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #8B6E2A;
    background: rgba(201,168,76,0.06);
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 8px;
  }}

  .footer {{
    text-align: center;
    padding: 48px;
    color: #4B5563;
    font-size: 11px;
    letter-spacing: 3px;
    text-transform: uppercase;
  }}
  .footer span {{ color: #C9A84C; }}
</style>
</head>
<body>

<div class="hero">
  <h1>Exhibition Content Production Brief</h1>
  <div class="sub">{company} &mdash; {today} &mdash; Generated by AUROS AI</div>
  <div class="stats">
    <div class="stat"><div class="stat-num">{len(all_results)}</div><div class="stat-lbl">Exhibitions</div></div>
    <div class="stat"><div class="stat-num">{total_scripts}</div><div class="stat-lbl">Video Scripts</div></div>
    <div class="stat"><div class="stat-num">{total_posts}</div><div class="stat-lbl">Social Posts</div></div>
    <div class="stat"><div class="stat-num">{total_hooks}</div><div class="stat-lbl">Hooks</div></div>
  </div>
</div>

{sections_html}

<div class="footer"><span>AUROS</span> &middot; Intelligence, Elevated</div>
</body>
</html>"""

    path = content_dir / f"exhibition_brief_{today}.html"
    path.write_text(html)
    print(f"[AUROS] Master production brief saved to {path}")


def run(company: str, **kwargs) -> dict:
    """Orchestrator-compatible entry point."""
    return generate_exhibition_content(company=company)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Exhibition Content Creator")
    parser.add_argument("--company", required=True)
    args = parser.parse_args()
    generate_exhibition_content(company=args.company)

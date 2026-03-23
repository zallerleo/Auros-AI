#!/usr/bin/env python3
"""
AUROS AI — Content Creator Agent
Generates actual marketing content: ad scripts, social posts, carousel copy,
hooks, captions, and email sequences — all powered by the knowledge base.

Usage:
    python -m agents.content_creator.content_agent --company "Company Name"
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
from agents.shared.client_config import load_client_config


def _load_latest_json(client_dir: Path, prefix: str) -> dict | None:
    files = sorted(client_dir.glob(f"{prefix}_*.json"), reverse=True)
    return json.loads(files[0].read_text()) if files else None


def _load_knowledge() -> str:
    try:
        from agents.shared.knowledge import get_frameworks_summary, get_benchmarks
        return get_frameworks_summary(["copywriting", "psychology", "video_marketing", "social_media"]) + "\n" + get_benchmarks()
    except Exception:
        return ""


# ─── VIDEO AD SCRIPTS ───

VIDEO_SCRIPTS_PROMPT = """You are an elite creative director at AUROS, the world's most data-driven marketing agency. Generate video ad scripts for {company}.

COMPANY CONTEXT:
{company_context}

MARKETING KNOWLEDGE (use these frameworks):
{knowledge}

Generate 3 video ad scripts with these exact lengths:

**SCRIPT 1: 15-SECOND (Instagram Reels / TikTok)**
Use the Hook-Value-Close structure. This is a scroll-stopper.
- 0-3s: Pattern interrupt hook (text overlay + visual)
- 3-12s: One powerful showcase moment
- 12-15s: CTA with urgency

**SCRIPT 2: 30-SECOND (Instagram / YouTube Pre-Roll)**
Use PAS (Problem-Agitate-Solution) framework.
- 0-5s: Problem hook that creates tension
- 5-15s: Agitate — show what they're missing
- 15-25s: Solution showcase with 3-4 cuts
- 25-30s: CTA + social proof

**SCRIPT 3: 60-SECOND (YouTube / Facebook)**
Use the Three-Act Video Structure.
- 0-5s: Cinematic hook
- 5-15s: Act 1 — Setup the desire
- 15-40s: Act 2 — The experience unfolds (4-5 visual moments)
- 40-50s: Act 3 — Transformation / proof
- 50-60s: CTA with emotion

For EACH script provide:
- Shot-by-shot breakdown with exact timestamps
- Text overlays (exact copy)
- Voiceover/narration (exact copy)
- Music direction (tempo, mood, reference)
- Visual direction for each shot (what to generate with AI tools)
- Platform-specific notes

Return valid JSON:
{{
  "company": "{company}",
  "scripts": [
    {{
      "id": "15s_reel",
      "duration": 15,
      "title": "...",
      "platform": "Instagram Reels / TikTok",
      "framework_used": "Hook-Value-Close",
      "shots": [
        {{
          "shot_number": 1,
          "timestamp": "0:00 - 0:03",
          "visual": "Detailed description for AI image/video generation",
          "text_overlay": "Exact text shown on screen",
          "voiceover": "Exact narration or null if music-only",
          "camera_motion": "zoom in / pan / static / orbit",
          "transition": "cut / crossfade / whip pan"
        }}
      ],
      "music_direction": {{
        "mood": "...",
        "tempo": "...",
        "reference": "Similar to...",
        "source": "Pixabay / Uppbeat"
      }},
      "hashtags": ["..."],
      "caption": "Full post caption with hooks and CTAs"
    }}
  ]
}}"""


# ─── SOCIAL MEDIA POSTS ───

SOCIAL_POSTS_PROMPT = """You are AUROS's head of social media content. Create a batch of 20 ready-to-post social media pieces for {company}.

COMPANY CONTEXT:
{company_context}

MARKETING KNOWLEDGE:
{knowledge}

Generate 20 posts across these categories:
- 5x Instagram Feed posts (carousel outlines + captions)
- 5x Instagram Reels concepts (hook + script + caption)
- 4x LinkedIn posts (thought leadership)
- 3x Instagram Stories (engagement-driven: polls, quizzes, Q&A)
- 3x Twitter/X posts (punchy, shareable)

For each post, apply the relevant copywriting framework (AIDA, PAS, BAB, etc.) and note which one you used.

Every post must have:
- A scroll-stopping hook (first line)
- The full copy/caption
- Relevant hashtags (10-15 for Instagram, 3-5 for LinkedIn)
- Best posting time
- Visual direction (what image/video to pair with it)
- Expected engagement driver (save, share, comment, or click)

Return valid JSON:
{{
  "company": "{company}",
  "batch_date": "{today}",
  "posts": [
    {{
      "id": 1,
      "platform": "instagram_feed",
      "type": "carousel",
      "framework_used": "AIDA",
      "hook": "First line that stops the scroll",
      "caption": "Full caption with line breaks",
      "hashtags": ["..."],
      "slides": ["Slide 1 text", "Slide 2 text"],
      "visual_direction": "Description for image generation",
      "posting_time": "Tuesday 11:00 AM",
      "engagement_driver": "save",
      "cta": "..."
    }}
  ],
  "content_themes": ["recurring themes across the batch"],
  "tone_notes": "Voice and tone guidelines used"
}}"""


# ─── HOOKS BANK ───

HOOKS_PROMPT = """You are AUROS's hook specialist. Create a bank of 30 scroll-stopping hooks for {company}.

COMPANY CONTEXT:
{company_context}

MARKETING KNOWLEDGE (psychology + copywriting):
{knowledge}

Generate 30 hooks organized by type:
- 6x Question hooks ("Have you ever wondered...")
- 6x Statistic hooks ("93% of people don't know...")
- 6x Contrarian hooks ("Stop doing X. Here's why...")
- 6x Story hooks ("We almost lost everything when...")
- 6x Visual hooks (describe opening shot that stops scrolling)

Each hook must:
- Work in the first 3 seconds (video) or first line (text)
- Be specific to the exhibition/experiential design industry
- Create an open loop that demands completion
- Note which psychological trigger it uses (curiosity, fear, FOMO, social proof, etc.)

Return valid JSON:
{{
  "company": "{company}",
  "hooks": [
    {{
      "id": 1,
      "type": "question",
      "hook_text": "...",
      "psychological_trigger": "curiosity",
      "best_for": "Instagram Reel / TikTok / LinkedIn",
      "follow_up_angle": "What this hook leads into"
    }}
  ]
}}"""


def generate_content(company: str) -> dict:
    """Generate all content for a company."""
    today = datetime.now().strftime("%Y-%m-%d")
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"
    content_dir = client_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # Load context
    audit = _load_latest_json(client_dir, "marketing_audit") or {}
    brand = _load_latest_json(client_dir, "brand_identity") or {}
    plan = _load_latest_json(client_dir, "marketing_plan") or {}

    # Load client config (with fallbacks for missing config)
    try:
        client_cfg = load_client_config(company)
    except FileNotFoundError:
        client_cfg = {}

    cfg_industry = client_cfg.get("industry", "experiential design / entertainment exhibitions")
    cfg_handles = client_cfg.get("social_handles", {})
    social_list = [cfg_handles.get("instagram", "")] + cfg_handles.get("other", [])
    social_list = [h for h in social_list if h]  # drop blanks

    company_context = json.dumps({
        "company": company,
        "industry": cfg_industry,
        "audit_summary": audit.get("executive_summary", ""),
        "swot": audit.get("swot", {}),
        "brand_colors": brand.get("colors", {}),
        "brand_voice": brand.get("voice", {}),
        "content_pillars": plan.get("content_strategy", {}).get("content_pillars", []),
        "target_audience": plan.get("target_audience", {}),
        "social_handles": social_list or ["@company"],
    }, indent=2)[:6000]

    knowledge = _load_knowledge()[:4000]
    results = {}

    # 1. Video Ad Scripts
    print("[AUROS] Generating video ad scripts (15s, 30s, 60s)...")
    prompt = VIDEO_SCRIPTS_PROMPT.format(
        company=company,
        company_context=company_context,
        knowledge=knowledge,
    )
    raw = generate(prompt, temperature=0.6, max_tokens=6000)
    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]
    scripts = json.loads(json_str)
    results["video_scripts"] = scripts

    scripts_path = content_dir / f"video_scripts_{today}.json"
    scripts_path.write_text(json.dumps(scripts, indent=2))
    print(f"[AUROS] Video scripts saved — {len(scripts.get('scripts', []))} scripts")

    # 2. Social Media Posts
    print("[AUROS] Generating 20 social media posts...")
    prompt = SOCIAL_POSTS_PROMPT.format(
        company=company,
        company_context=company_context,
        knowledge=knowledge,
        today=today,
    )
    raw = generate(prompt, temperature=0.7, max_tokens=8000)
    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]
    posts = json.loads(json_str)
    results["social_posts"] = posts

    posts_path = content_dir / f"social_posts_{today}.json"
    posts_path.write_text(json.dumps(posts, indent=2))
    print(f"[AUROS] Social posts saved — {len(posts.get('posts', []))} posts")

    # 3. Hooks Bank
    print("[AUROS] Generating hooks bank (30 hooks)...")
    prompt = HOOKS_PROMPT.format(
        company=company,
        company_context=company_context,
        knowledge=knowledge,
    )
    raw = generate(prompt, temperature=0.7, max_tokens=4096)
    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]
    hooks = json.loads(json_str)
    results["hooks"] = hooks

    hooks_path = content_dir / f"hooks_bank_{today}.json"
    hooks_path.write_text(json.dumps(hooks, indent=2))
    print(f"[AUROS] Hooks bank saved — {len(hooks.get('hooks', []))} hooks")

    # 4. Generate master content brief (HTML)
    print("[AUROS] Building content production brief...")
    _render_content_brief(company, scripts, posts, hooks, brand, content_dir, today)

    print(f"[AUROS] Content Creator complete — all assets in {content_dir}")
    return results


def _render_content_brief(
    company: str,
    scripts: dict,
    posts: dict,
    hooks: dict,
    brand: dict,
    content_dir: Path,
    today: str,
) -> None:
    """Render all content into a beautiful HTML production brief."""
    primary_color = "#B80021"
    colors = brand.get("colors", {})
    if colors.get("primary"):
        primary_color = colors["primary"][0].get("hex", "#B80021")

    # Build scripts HTML
    scripts_html = ""
    for script in scripts.get("scripts", []):
        shots_html = ""
        for shot in script.get("shots", []):
            shots_html += f"""
            <div class="shot">
              <div class="shot-time">{shot.get('timestamp', '')}</div>
              <div class="shot-details">
                <div class="shot-visual">{shot.get('visual', '')}</div>
                {f'<div class="shot-text">TEXT: {shot.get("text_overlay", "")}</div>' if shot.get("text_overlay") else ""}
                {f'<div class="shot-vo">VO: {shot.get("voiceover", "")}</div>' if shot.get("voiceover") else ""}
                <div class="shot-camera">{shot.get('camera_motion', '')} &rarr; {shot.get('transition', '')}</div>
              </div>
            </div>"""

        music = script.get("music_direction", {})
        scripts_html += f"""
        <div class="script-card">
          <div class="script-header">
            <h3>{script.get('title', script.get('id', ''))}</h3>
            <div class="script-meta">
              <span class="badge">{script.get('duration', '')}s</span>
              <span class="badge">{script.get('platform', '')}</span>
              <span class="badge framework">{script.get('framework_used', '')}</span>
            </div>
          </div>
          <div class="shots-timeline">{shots_html}</div>
          <div class="music-note">
            Music: {music.get('mood', '')} &middot; {music.get('tempo', '')} &middot; Ref: {music.get('reference', '')}
          </div>
          {f'<div class="caption-preview">{script.get("caption", "")[:200]}</div>' if script.get("caption") else ""}
        </div>"""

    # Build posts HTML
    posts_html = ""
    for post in posts.get("posts", [])[:10]:
        posts_html += f"""
        <div class="post-card">
          <div class="post-header">
            <span class="badge">{post.get('platform', '').replace('_', ' ').title()}</span>
            <span class="badge">{post.get('type', '')}</span>
            <span class="badge framework">{post.get('framework_used', '')}</span>
          </div>
          <div class="post-hook">{post.get('hook', '')}</div>
          <div class="post-caption">{post.get('caption', '')[:300]}...</div>
          <div class="post-meta">
            <span>Post at: {post.get('posting_time', '')}</span>
            <span>Driver: {post.get('engagement_driver', '')}</span>
          </div>
        </div>"""

    # Build hooks HTML
    hooks_html = ""
    for hook in hooks.get("hooks", [])[:15]:
        hooks_html += f"""
        <div class="hook-item">
          <div class="hook-type">{hook.get('type', '').upper()}</div>
          <div class="hook-text">"{hook.get('hook_text', '')}"</div>
          <div class="hook-meta">
            <span class="badge">{hook.get('psychological_trigger', '')}</span>
            <span class="badge">{hook.get('best_for', '')}</span>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUROS Content Production Brief — {company}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Inter', sans-serif; background: #0B0F1A; color: #FAFAF8; }}

  .header {{
    padding: 48px 40px;
    border-bottom: 1px solid rgba(201,168,76,0.15);
    background: linear-gradient(135deg, #0B0F1A 0%, #111827 100%);
  }}
  .header h1 {{ font-size: 32px; font-weight: 900; color: #C9A84C; letter-spacing: -1px; }}
  .header p {{ color: #9CA3AF; margin-top: 8px; font-size: 14px; }}
  .header .stats {{ display: flex; gap: 32px; margin-top: 20px; }}
  .header .stat-box {{ text-align: center; }}
  .header .stat-num {{ font-size: 28px; font-weight: 900; color: #C9A84C; }}
  .header .stat-lbl {{ font-size: 10px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #6B7280; margin-top: 4px; }}

  .section {{ padding: 40px; border-bottom: 1px solid rgba(255,255,255,0.05); }}
  .section-title {{ font-size: 11px; font-weight: 700; letter-spacing: 4px; text-transform: uppercase; color: #8B6E2A; margin-bottom: 24px; }}

  .badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; background: rgba(255,255,255,0.05); color: #9CA3AF; margin-right: 6px; }}
  .badge.framework {{ background: rgba(201,168,76,0.1); color: #C9A84C; }}

  /* Scripts */
  .script-card {{ background: #111827; border: 1px solid rgba(201,168,76,0.1); border-radius: 14px; padding: 24px; margin-bottom: 20px; }}
  .script-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 10px; }}
  .script-header h3 {{ font-size: 18px; font-weight: 800; }}
  .shots-timeline {{ border-left: 2px solid rgba(201,168,76,0.2); padding-left: 20px; margin: 16px 0; }}
  .shot {{ display: flex; gap: 14px; margin-bottom: 14px; padding-bottom: 14px; border-bottom: 1px solid rgba(255,255,255,0.03); }}
  .shot-time {{ font-size: 12px; font-weight: 700; color: #C9A84C; min-width: 90px; flex-shrink: 0; }}
  .shot-visual {{ font-size: 13px; color: #E0E0E0; line-height: 1.5; }}
  .shot-text {{ font-size: 13px; color: #E8C96A; font-weight: 700; margin-top: 6px; }}
  .shot-vo {{ font-size: 13px; color: #9CA3AF; font-style: italic; margin-top: 4px; }}
  .shot-camera {{ font-size: 11px; color: #6B7280; margin-top: 4px; }}
  .music-note {{ font-size: 12px; color: #6B7280; padding: 10px 14px; background: rgba(201,168,76,0.04); border-radius: 8px; margin-top: 12px; }}
  .caption-preview {{ font-size: 12px; color: #9CA3AF; margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.05); line-height: 1.5; }}

  /* Posts */
  .posts-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 14px; }}
  .post-card {{ background: #111827; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 20px; }}
  .post-header {{ margin-bottom: 10px; }}
  .post-hook {{ font-size: 16px; font-weight: 800; color: #FAFAF8; line-height: 1.4; margin-bottom: 10px; }}
  .post-caption {{ font-size: 13px; color: #9CA3AF; line-height: 1.6; white-space: pre-line; }}
  .post-meta {{ display: flex; justify-content: space-between; margin-top: 12px; font-size: 11px; color: #6B7280; }}

  /* Hooks */
  .hooks-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }}
  .hook-item {{ background: #111827; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px; }}
  .hook-type {{ font-size: 10px; font-weight: 700; letter-spacing: 2px; color: #8B6E2A; margin-bottom: 8px; }}
  .hook-text {{ font-size: 15px; font-weight: 700; color: #FAFAF8; line-height: 1.4; margin-bottom: 10px; }}
  .hook-meta {{ display: flex; gap: 6px; }}

  .footer {{ text-align: center; padding: 40px; color: #6B7280; font-size: 11px; letter-spacing: 3px; text-transform: uppercase; }}
  .footer span {{ color: #C9A84C; }}
</style>
</head>
<body>

<div class="header">
  <h1>Content Production Brief</h1>
  <p>{company} &mdash; Generated {today} by AUROS AI</p>
  <div class="stats">
    <div class="stat-box"><div class="stat-num">{len(scripts.get('scripts', []))}</div><div class="stat-lbl">Video Scripts</div></div>
    <div class="stat-box"><div class="stat-num">{len(posts.get('posts', []))}</div><div class="stat-lbl">Social Posts</div></div>
    <div class="stat-box"><div class="stat-num">{len(hooks.get('hooks', []))}</div><div class="stat-lbl">Hooks</div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">Video Ad Scripts</div>
  {scripts_html}
</div>

<div class="section">
  <div class="section-title">Social Media Posts (showing 10 of {len(posts.get('posts', []))})</div>
  <div class="posts-grid">{posts_html}</div>
</div>

<div class="section">
  <div class="section-title">Hooks Bank (showing 15 of {len(hooks.get('hooks', []))})</div>
  <div class="hooks-grid">{hooks_html}</div>
</div>

<div class="footer"><span>AUROS</span> &middot; Intelligence, Elevated</div>

</body>
</html>"""

    path = content_dir / f"content_brief_{today}.html"
    path.write_text(html)
    print(f"[AUROS] Content production brief saved to {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Content Creator")
    parser.add_argument("--company", required=True)
    args = parser.parse_args()
    generate_content(company=args.company)

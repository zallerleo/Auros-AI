"""
AUROS AI — Central Configuration
Loads environment variables and brand tokens for all agents.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Project root — walk up until we find .env or brand/ directory
def _find_project_root() -> Path:
    p = Path(__file__).resolve().parent
    for _ in range(10):
        if (p / ".env").exists() or (p / "brand").is_dir():
            return p
        p = p.parent
    return Path(__file__).resolve().parent.parent.parent

PROJECT_ROOT = _find_project_root()
load_dotenv(PROJECT_ROOT / ".env", override=True)

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

# Lead Gen & Website Pipeline
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
NETLIFY_TOKEN = os.getenv("NETLIFY_TOKEN", "")

# Email
NEWSLETTER_RECIPIENT = os.getenv("NEWSLETTER_RECIPIENT", "leo@auros.ai")
NEWSLETTER_FROM = os.getenv("NEWSLETTER_FROM", "newsletter@auros.ai")
REPORT_RECIPIENT = os.getenv("REPORT_RECIPIENT", "leo@auros.ai")

# Gmail
GMAIL_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", str(PROJECT_ROOT / "credentials.json"))

# Paths
BRAND_DIR = PROJECT_ROOT / "brand"
NEWSLETTER_DIR = PROJECT_ROOT / "agents" / "newsletter"
MARKET_DIR = PROJECT_ROOT / "agents" / "market_analysis"
QUALITY_DIR = PROJECT_ROOT / "agents" / "quality_checker"
GEO_DIR = PROJECT_ROOT / "agents" / "geo_monitor"
PORTFOLIO_DIR = PROJECT_ROOT / "portfolio"
LOGS_DIR = PROJECT_ROOT / "logs"

# Brand tokens
def load_brand_tokens() -> dict:
    """Load AUROS brand tokens from colors.json."""
    tokens_path = BRAND_DIR / "colors.json"
    with open(tokens_path) as f:
        return json.load(f)

BRAND = load_brand_tokens()

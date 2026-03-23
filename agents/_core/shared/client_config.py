"""
AUROS AI — Client Configuration Loader
Reads per-client config from portfolio/client_{slug}/client_config.json.
"""

import json
import re
from pathlib import Path
from typing import Optional

from agents._core.shared.config import PROJECT_ROOT, PORTFOLIO_DIR


# ---------------------------------------------------------------------------
# Defaults — returned for any field missing from the JSON file
# ---------------------------------------------------------------------------
_DEFAULTS: dict = {
    "company_name": "",
    "slug": "",
    "industry": "",
    "website": "",
    "social_handles": {"instagram": "", "other": []},
    "email_recipients": [],
    "products": [],
    "target_platforms": ["instagram"],
    "default_tone": "",
    "pipeline_config": {
        "newsletter_recipient": "",
        "report_recipient": "",
    },
}


def _slugify(name: str) -> str:
    """Convert a human-readable company name to a filesystem slug.

    Example: "The Imagine Team" -> "the_imagine_team"
    """
    s = name.strip().lower()
    s = re.sub(r"[^\w\s]", "", s)   # drop non-alphanumeric/non-space
    s = re.sub(r"\s+", "_", s)      # spaces -> underscores
    s = re.sub(r"_+", "_", s)       # collapse runs of underscores
    return s.strip("_")


def _deep_merge(defaults: dict, overrides: dict) -> dict:
    """Recursively merge *overrides* into *defaults* (non-destructive)."""
    merged = dict(defaults)
    for key, value in overrides.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_client_dir(company: str) -> Path:
    """Return the portfolio directory for a client.

    Parameters
    ----------
    company : str
        Human-readable company name **or** slug.

    Returns
    -------
    Path
        e.g. ``<PROJECT_ROOT>/portfolio/client_the_imagine_team``
    """
    slug = _slugify(company)
    return PORTFOLIO_DIR / f"client_{slug}"


def load_client_config(company: str) -> dict:
    """Load and return the client configuration dictionary.

    Converts *company* to a slug, reads
    ``portfolio/client_{slug}/client_config.json``, and back-fills any
    missing keys with sensible defaults so downstream code never has to
    worry about ``KeyError``.

    Parameters
    ----------
    company : str
        Human-readable company name **or** slug.

    Returns
    -------
    dict
        Fully-populated configuration dictionary.

    Raises
    ------
    FileNotFoundError
        If the config JSON does not exist on disk.
    """
    client_dir = get_client_dir(company)
    config_path = client_dir / "client_config.json"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Client config not found: {config_path}\n"
            f"Create one by copying portfolio/_template/client_config.json"
        )

    with open(config_path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    return _deep_merge(_DEFAULTS, raw)


def get_product(company: str, product_slug: str) -> Optional[dict]:
    """Return a single product dict from the client config, or None."""
    cfg = load_client_config(company)
    for product in cfg.get("products", []):
        if product.get("slug") == product_slug:
            return product
    return None


def list_clients() -> list[str]:
    """Scan the portfolio directory and return a list of client slugs.

    Only directories matching the ``client_*`` naming convention that
    contain a ``client_config.json`` file are included.
    """
    clients: list[str] = []
    if not PORTFOLIO_DIR.is_dir():
        return clients
    for child in sorted(PORTFOLIO_DIR.iterdir()):
        if child.is_dir() and child.name.startswith("client_"):
            if (child / "client_config.json").exists():
                slug = child.name.removeprefix("client_")
                clients.append(slug)
    return clients

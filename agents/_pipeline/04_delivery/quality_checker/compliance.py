"""
AUROS AI — EU AI Act Compliance Module
Checks content for regulatory compliance and generates audit trails.

Usage:
    from agents.quality_checker.compliance import check_compliance, create_audit_trail
"""

from __future__ import annotations

import re
import json
import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUDIT_TRAIL_PATH = Path(__file__).resolve().parent / "audit_trail.jsonl"

# Patterns that may indicate personal data
_PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\+?\d[\d\s\-()]{7,}\d"),
    "national_id": re.compile(r"\b\d{3}[\s-]?\d{2}[\s-]?\d{4}\b"),  # SSN-like
    "iban": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b"),
    "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
}

# Terms that signal manipulative intent under the AI Act
_MANIPULATION_SIGNALS = [
    "subliminal",
    "exploit vulnerabilities",
    "dark pattern",
    "urgency scarcity",
    "false countdown",
    "fake social proof",
    "fabricated testimonial",
    "hidden persuasion",
    "deceptive",
    "misleading claim",
    "guaranteed results",
    "act now or lose",
    "only 1 left",
    "everyone is buying",
]

# Content types that require AI disclosure under the Act
_DISCLOSURE_REQUIRED_TYPES = {
    "ad",
    "advertisement",
    "email",
    "social_post",
    "blog",
    "article",
    "landing_page",
    "chatbot_response",
    "product_description",
    "press_release",
}

# Disclosure templates by content type
_DISCLOSURE_TEMPLATES: dict[str, str] = {
    "ad": (
        "This advertisement was generated with the assistance of artificial intelligence. "
        "AUROS AI | Transparency notice under EU AI Act."
    ),
    "advertisement": (
        "This advertisement was generated with the assistance of artificial intelligence. "
        "AUROS AI | Transparency notice under EU AI Act."
    ),
    "email": (
        "This email was composed with AI assistance. "
        "For more information about our use of AI, visit our transparency page."
    ),
    "social_post": (
        "#AIGenerated — This content was created with AI assistance by AUROS AI."
    ),
    "blog": (
        "Disclosure: This article was produced with the assistance of artificial "
        "intelligence tools. All facts have been reviewed by a human editor."
    ),
    "article": (
        "Disclosure: This article was produced with the assistance of artificial "
        "intelligence tools. All facts have been reviewed by a human editor."
    ),
    "landing_page": (
        "Parts of this page were generated using AI. "
        "AUROS AI is committed to transparency under the EU AI Act."
    ),
    "chatbot_response": (
        "You are interacting with an AI-powered assistant. "
        "A human agent is available upon request."
    ),
    "product_description": (
        "This product description was drafted with AI assistance and reviewed for accuracy."
    ),
    "press_release": (
        "Disclosure: AI tools were used in the preparation of this press release. "
        "All statements have been verified by the issuing organization."
    ),
}

_DEFAULT_DISCLOSURE = (
    "This content was generated with the assistance of artificial intelligence. "
    "AUROS AI | EU AI Act transparency notice."
)


# ---------------------------------------------------------------------------
# Disclosure detection
# ---------------------------------------------------------------------------

_DISCLOSURE_MARKERS = [
    "ai-generated",
    "ai generated",
    "generated with ai",
    "artificial intelligence",
    "created with ai",
    "ai assistance",
    "ai-assisted",
    "produced with ai",
    "#aigenerated",
    "transparency notice",
    "ai disclosure",
]


def _has_disclosure(content: str) -> bool:
    """Check whether content already contains an AI disclosure."""
    content_lower = content.lower()
    return any(marker in content_lower for marker in _DISCLOSURE_MARKERS)


# ---------------------------------------------------------------------------
# PII detection
# ---------------------------------------------------------------------------


def _find_pii(content: str) -> list[dict]:
    """Scan content for personal data patterns."""
    findings = []
    for category, pattern in _PII_PATTERNS.items():
        matches = pattern.findall(content)
        if matches:
            findings.append({
                "category": category,
                "count": len(matches),
                "samples": [m[:4] + "***" for m in matches[:3]],  # Redacted samples
            })
    return findings


# ---------------------------------------------------------------------------
# Manipulation check
# ---------------------------------------------------------------------------


def _find_manipulation_signals(content: str) -> list[str]:
    """Detect phrases that could be considered manipulative under the AI Act."""
    content_lower = content.lower()
    return [
        signal for signal in _MANIPULATION_SIGNALS
        if signal in content_lower
    ]


# ---------------------------------------------------------------------------
# Transparency check
# ---------------------------------------------------------------------------

_AUTOMATED_DECISION_MARKERS = [
    "automatically selected",
    "algorithm chose",
    "personalized for you",
    "tailored recommendation",
    "ai-selected",
    "machine learning model",
    "automated decision",
    "algorithmically ranked",
    "predicted preference",
]


def _check_transparency(content: str) -> dict:
    """Check whether automated decision-making is disclosed."""
    content_lower = content.lower()
    detected = [
        marker for marker in _AUTOMATED_DECISION_MARKERS
        if marker in content_lower
    ]
    if not detected:
        return {"has_automated_decisions": False, "disclosed": True, "markers": []}

    # If automated decisions are mentioned, check that disclosure exists
    has_disclosure = _has_disclosure(content)
    return {
        "has_automated_decisions": True,
        "disclosed": has_disclosure,
        "markers": detected,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_compliance(
    content: str = "",
    content_type: str = "ad",
    company: str = "",
    **kwargs,
) -> dict:
    """
    Check content for EU AI Act compliance.

    Args:
        content: The text content to check.
        content_type: Type of content (e.g. 'ad', 'email', 'blog').
        company: When called by orchestrator, scans portfolio for content.

    Returns:
        Compliance report dict with score, issues, and recommendations.
    """
    # If called from orchestrator with just company, load sample content
    if company and not content:
        from agents.shared.config import PORTFOLIO_DIR
        slug = company.lower().replace(" ", "_").replace("'", "")
        client_dir = PORTFOLIO_DIR / f"client_{slug}"
        for candidate in sorted(client_dir.rglob("proposal_*.html")):
            content = candidate.read_text()[:5000]
            content_type = "proposal"
            break
        if not content:
            return {"score": 100, "status": "pass", "note": "No content found to check"}
    issues: list[dict] = []
    recommendations: list[str] = []
    required_disclosures: list[str] = []

    # 1. AI disclosure check
    needs_disclosure = content_type.lower() in _DISCLOSURE_REQUIRED_TYPES
    has_disc = _has_disclosure(content)

    if needs_disclosure and not has_disc:
        issues.append({
            "category": "ai_disclosure",
            "severity": "high",
            "detail": (
                f"Content type '{content_type}' requires an AI-generated "
                f"disclosure under the EU AI Act, but none was found."
            ),
        })
        disclosure_text = generate_disclosure(content_type)
        required_disclosures.append(disclosure_text)
        recommendations.append(
            f"Add the following disclosure to the {content_type}: "
            f"'{disclosure_text}'"
        )

    # 2. Personal data check
    pii_findings = _find_pii(content)
    if pii_findings:
        for finding in pii_findings:
            issues.append({
                "category": "personal_data",
                "severity": "high",
                "detail": (
                    f"Detected {finding['count']} instance(s) of "
                    f"{finding['category']} data."
                ),
            })
        recommendations.append(
            "Remove or anonymize personal data before publishing. "
            "Ensure GDPR-compliant consent if personal data is required."
        )

    # 3. Transparency check
    transparency = _check_transparency(content)
    if transparency["has_automated_decisions"] and not transparency["disclosed"]:
        issues.append({
            "category": "transparency",
            "severity": "medium",
            "detail": (
                "Content references automated decision-making "
                f"({', '.join(transparency['markers'])}) without proper disclosure."
            ),
        })
        recommendations.append(
            "Add a transparency notice explaining how automated "
            "decisions are made and how users can request human review."
        )

    # 4. Manipulation check
    manipulation_signals = _find_manipulation_signals(content)
    if manipulation_signals:
        issues.append({
            "category": "manipulation",
            "severity": "critical",
            "detail": (
                f"Potentially manipulative techniques detected: "
                f"{', '.join(manipulation_signals)}. These may violate "
                f"Article 5 of the EU AI Act."
            ),
        })
        recommendations.append(
            "Remove manipulative language immediately. The EU AI Act "
            "prohibits AI systems that deploy subliminal, manipulative, "
            "or deceptive techniques."
        )

    # Score calculation
    score = 100
    severity_penalties = {"critical": 40, "high": 20, "medium": 10, "low": 5}
    for issue in issues:
        score -= severity_penalties.get(issue["severity"], 5)
    score = max(score, 0)

    compliant = score >= 70 and not any(
        i["severity"] == "critical" for i in issues
    )

    return {
        "compliant": compliant,
        "score": score,
        "content_type": content_type,
        "issues": issues,
        "required_disclosures": required_disclosures,
        "recommendations": recommendations,
        "checks_performed": [
            "ai_disclosure",
            "personal_data",
            "transparency",
            "manipulation",
        ],
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def generate_disclosure(content_type: str) -> str:
    """
    Return the appropriate AI disclosure text for a content type.

    Args:
        content_type: Type of content (e.g. 'ad', 'email', 'blog').

    Returns:
        Disclosure string ready to append to the content.
    """
    return _DISCLOSURE_TEMPLATES.get(content_type.lower(), _DEFAULT_DISCLOSURE)


def create_audit_trail(
    agent_name: str,
    input_summary: str,
    output_summary: str,
    model_used: str,
) -> dict:
    """
    Create and persist an audit trail entry for an agent run.

    Args:
        agent_name: Name of the agent that ran.
        input_summary: Brief description of the input.
        output_summary: Brief description of the output.
        model_used: LLM model identifier used.

    Returns:
        The audit trail entry dict.
    """
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "agent_name": agent_name,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "model_used": model_used,
        "framework": "EU AI Act",
        "version": "1.0",
    }

    AUDIT_TRAIL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_TRAIL_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry

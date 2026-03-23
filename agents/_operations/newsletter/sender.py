"""
AUROS AI — Email Sender
Sends newsletters via Resend API (primary) or Gmail API (fallback).
"""

from __future__ import annotations

import resend
from agents.shared.config import RESEND_API_KEY, NEWSLETTER_FROM, NEWSLETTER_RECIPIENT


def send_via_resend(subject: str, html_content: str, to: str | None = None) -> dict:
    """Send an email via Resend API."""
    resend.api_key = RESEND_API_KEY
    recipient = to or NEWSLETTER_RECIPIENT

    response = resend.Emails.send({
        "from": NEWSLETTER_FROM,
        "to": [recipient],
        "subject": subject,
        "html": html_content,
    })
    return response


def send_newsletter(subject: str, html_content: str, to: str | None = None) -> dict:
    """Send newsletter email. Uses Resend as primary sender."""
    try:
        result = send_via_resend(subject, html_content, to)
        print(f"[AUROS] Newsletter sent successfully via Resend to {to or NEWSLETTER_RECIPIENT}")
        return {"status": "sent", "method": "resend", "result": result}
    except Exception as e:
        print(f"[AUROS] Resend failed: {e}")
        return {"status": "failed", "method": "resend", "error": str(e)}

"""Generic outbound email helper.

Delivery order: the Resend-style HTTP API (EMAIL_API_URL + EMAIL_API_KEY)
first, then SMTP (SMTP_HOST/PORT/USER/PASS/SENDER) as a fallback. Never
raises — returns True/False so callers can degrade gracefully.
"""
import smtplib
from email.mime.text import MIMEText

import httpx

from app.config import settings


async def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email to ``to``. Returns False (no raise) when
    the delivery fails or no email service is configured."""
    if settings.EMAIL_API_URL:
        try:
            headers = {}
            if settings.EMAIL_API_KEY:
                headers["Authorization"] = f"Bearer {settings.EMAIL_API_KEY}"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    settings.EMAIL_API_URL,
                    json={"to": to, "subject": subject, "text": body},
                    headers=headers,
                )
                return resp.is_success
        except Exception:
            return False

    if settings.SMTP_HOST:
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_SENDER
            msg["To"] = to
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.starttls()
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.sendmail(settings.SMTP_SENDER, [to], msg.as_string())
            return True
        except Exception:
            return False

    return False


def email_configured() -> bool:
    """Whether any outbound email transport is configured."""
    return bool(settings.EMAIL_API_URL or settings.SMTP_HOST)

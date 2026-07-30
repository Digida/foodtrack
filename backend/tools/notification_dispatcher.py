from __future__ import annotations

import json
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Any

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


async def send_notification(
    recipient: str,
    subject: str,
    message: str,
    channel: str = "email",
    email_config: dict | None = None,
    webhook_url: str | None = None,
) -> dict:
    channel = channel.lower()

    if channel == "email":
        config = email_config or {}
        sender = config.get("sender", "noreply@foodtrack.ae")
        smtp_host = config.get("smtp_host", "")
        smtp_port = config.get("smtp_port", 587)
        smtp_user = config.get("smtp_user", "")
        smtp_pass = config.get("smtp_pass", "")

        if smtp_host:
            try:
                msg = MIMEText(message)
                msg["Subject"] = subject
                msg["From"] = sender
                msg["To"] = recipient

                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    if smtp_user:
                        server.login(smtp_user, smtp_pass)
                    server.sendmail(sender, [recipient], msg.as_string())

                return {"status": "ok", "channel": "email", "recipient": recipient, "subject": subject}
            except Exception as e:
                return {"status": "error", "channel": "email", "message": str(e)}

        return {
            "status": "logged",
            "channel": "email",
            "recipient": recipient,
            "subject": subject,
            "message": message[:200],
            "note": "No SMTP configured; notification logged",
        }

    elif channel == "webhook":
        if not webhook_url:
            return {"status": "error", "message": "webhook_url required for webhook channel"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(webhook_url, json={"subject": subject, "message": message})
                resp.raise_for_status()
                return {"status": "ok", "channel": "webhook", "url": webhook_url}
        except Exception as e:
            return {"status": "error", "channel": "webhook", "message": str(e)}

    return {"status": "error", "message": f"Unknown channel: {channel}"}


class NotificationDispatcherTool(BaseTool):
    name = "notification_dispatcher"
    description = "Send notifications via email or webhook for supply chain events"
    parameters = {
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "Email recipient or identifier"},
            "subject": {"type": "string", "description": "Notification subject"},
            "message": {"type": "string", "description": "Notification body text"},
            "channel": {
                "type": "string",
                "enum": ["email", "webhook"],
                "description": "Delivery channel",
            },
            "email_config": {
                "type": "object",
                "description": "SMTP config: {smtp_host, smtp_port, smtp_user, smtp_pass, sender}",
            },
            "webhook_url": {"type": "string", "description": "Webhook URL for webhook channel"},
        },
        "required": ["recipient", "subject", "message"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        import asyncio
        result = asyncio.run(send_notification(
            kwargs.get("recipient", ""),
            kwargs.get("subject", ""),
            kwargs.get("message", ""),
            kwargs.get("channel", "email"),
            kwargs.get("email_config"),
            kwargs.get("webhook_url"),
        ))
        return json.dumps(result, ensure_ascii=False)

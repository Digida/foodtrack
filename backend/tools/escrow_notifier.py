"""Escrow Notifier Tool — builds escrow lifecycle notifications.

Constructs the human-readable message for an escrow lifecycle event
(required, deposited, held, released, refunded) and, when an SMTP/webhook
transport is supplied, dispatches it through the notification_dispatcher tool.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

ESCROW_MESSAGES = {
    "required": "Investor escrow is required on register {register}: {amount} {currency} must be deposited.",
    "deposited": "Escrow deposited on register {register}: {amount} {currency} is now held by the platform.",
    "held": "Escrow is held on register {register} ({amount} {currency}) pending buyer delivery.",
    "released": "Escrow released on register {register}: {amount} {currency} paid to the seller.",
    "refunded": "Escrow refunded on register {register}: {amount} {currency} returned to the buyer.",
}


def escrow_event_notification(
    event: str = "held",
    register_number: str | None = None,
    amount: float = 0.0,
    currency: str = "USD",
    recipient: str | None = None,
    subject: str | None = None,
    send: bool = False,
    email_config: dict | None = None,
    webhook_url: str | None = None,
) -> dict:
    """Build (and optionally send) an escrow lifecycle notification."""
    event = (event or "held").lower()
    if event not in ESCROW_MESSAGES:
        return {"status": "error", "message": f"Unknown escrow event '{event}'"}

    body = ESCROW_MESSAGES[event].format(
        register=register_number or "the register",
        amount=round(float(amount or 0), 2),
        currency=currency or "USD",
    )
    subject = subject or f"Escrow {event} — FoodTrack"
    result = {
        "status": "ok",
        "event": event,
        "subject": subject,
        "message": body,
        "register_number": register_number,
        "amount": round(float(amount or 0), 2),
        "currency": currency or "USD",
    }

    if send:
        from tools.notification_dispatcher import send_notification

        delivered = send_notification(
            recipient or "notify@foodtrack.local",
            subject,
            body,
            channel="email" if not webhook_url else "webhook",
            email_config=email_config,
            webhook_url=webhook_url,
        )
        if isinstance(delivered, dict) and hasattr(delivered, "__await__"):
            import asyncio

            delivered = asyncio.run(delivered)
        result["delivered"] = delivered

    return result


class EscrowNotifierTool(BaseTool):
    name = "escrow_notifier"
    description = (
        "Build escrow lifecycle notifications (required/deposited/held/released/"
        "refunded) and optionally dispatch them via the notification dispatcher."
    )
    parameters = {
        "type": "object",
        "properties": {
            "event": {
                "type": "string",
                "enum": ["required", "deposited", "held", "released", "refunded"],
                "description": "Escrow lifecycle event",
            },
            "register_number": {"type": "string", "description": "Register number"},
            "amount": {"type": "number", "description": "Escrow amount"},
            "currency": {"type": "string", "description": "Currency code (default USD)"},
            "recipient": {"type": "string", "description": "Notification recipient"},
            "subject": {"type": "string", "description": "Override subject"},
            "send": {"type": "boolean", "description": "Dispatch via notification dispatcher"},
            "email_config": {"type": "object", "description": "SMTP config for dispatch"},
            "webhook_url": {"type": "string", "description": "Webhook URL for dispatch"},
        },
        "required": ["event"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        import asyncio

        async def _run():
            from tools.notification_dispatcher import send_notification

            result = escrow_event_notification(
                kwargs.get("event", "held"),
                kwargs.get("register_number"),
                kwargs.get("amount", 0),
                kwargs.get("currency", "USD"),
                kwargs.get("recipient"),
                kwargs.get("subject"),
                False,
                kwargs.get("email_config"),
                kwargs.get("webhook_url"),
            )
            if kwargs.get("send"):
                delivered = await send_notification(
                    kwargs.get("recipient") or "notify@foodtrack.local",
                    result["subject"],
                    result["message"],
                    channel="email" if not kwargs.get("webhook_url") else "webhook",
                    email_config=kwargs.get("email_config"),
                    webhook_url=kwargs.get("webhook_url"),
                )
                result["delivered"] = delivered
            return result

        return json.dumps(asyncio.run(_run()), ensure_ascii=False)

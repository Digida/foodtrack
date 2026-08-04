"""Settlement Notifier Tool — builds settlement lifecycle notifications.

Constructs the human-readable message for a settlement lifecycle event
(created, due, paid, failed) and, when an SMTP/webhook transport is supplied,
dispatches it through the notification_dispatcher tool.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

SETTLEMENT_MESSAGES = {
    "created": "Settlement {settlement} created for {payee}: {amount} {currency} will be due on {due_date}.",
    "due": "Settlement {settlement} is due today for {payee}: {amount} {currency}.",
    "paid": "Settlement {settlement} paid to {payee}: {amount} {currency}.",
    "failed": "Settlement {settlement} failed for {payee}: {amount} {currency} could not be paid.",
}


def settlement_event_notification(
    event: str = "paid",
    settlement_number: str | None = None,
    payee_name: str | None = None,
    amount: float = 0.0,
    currency: str = "USD",
    due_date: str | None = None,
    recipient: str | None = None,
    subject: str | None = None,
    send: bool = False,
    email_config: dict | None = None,
    webhook_url: str | None = None,
) -> dict:
    """Build (and optionally send) a settlement lifecycle notification."""
    event = (event or "paid").lower()
    if event not in SETTLEMENT_MESSAGES:
        return {"status": "error", "message": f"Unknown settlement event '{event}'"}

    body = SETTLEMENT_MESSAGES[event].format(
        settlement=settlement_number or "the settlement",
        payee=payee_name or "the seller",
        amount=round(float(amount or 0), 2),
        currency=currency or "USD",
        due_date=due_date or "the due date",
    )
    subject = subject or f"Settlement {event} — FoodTrack"
    result = {
        "status": "ok",
        "event": event,
        "subject": subject,
        "message": body,
        "settlement_number": settlement_number,
        "payee_name": payee_name,
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


class SettlementNotifierTool(BaseTool):
    name = "settlement_notifier"
    description = (
        "Build settlement lifecycle notifications (created/due/paid/failed) and "
        "optionally dispatch them via the notification dispatcher."
    )
    parameters = {
        "type": "object",
        "properties": {
            "event": {
                "type": "string",
                "enum": ["created", "due", "paid", "failed"],
                "description": "Settlement lifecycle event",
            },
            "settlement_number": {"type": "string", "description": "Settlement number"},
            "payee_name": {"type": "string", "description": "Payee (seller) name"},
            "amount": {"type": "number", "description": "Settlement amount"},
            "currency": {"type": "string", "description": "Currency code (default USD)"},
            "due_date": {"type": "string", "description": "Due date"},
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

            result = settlement_event_notification(
                kwargs.get("event", "paid"),
                kwargs.get("settlement_number"),
                kwargs.get("payee_name"),
                kwargs.get("amount", 0),
                kwargs.get("currency", "USD"),
                kwargs.get("due_date"),
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

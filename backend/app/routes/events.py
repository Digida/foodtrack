import json

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.events import WebhookEvent
from app.services.event_service import (
    publish_event,
    subscribe_ws,
    unsubscribe_ws,
    register_webhook,
    list_webhooks,
    delete_webhook,
    list_event_logs,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/publish")
async def api_publish_event(
    event_type: str = Query(...),
    channel: str = Query(...),
    payload: str = Query("{}"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload_dict = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    try:
        return await publish_event(db, user, event_type, channel, payload_dict)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    await websocket.accept()
    await subscribe_ws(channel, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"echo": data}))
    except WebSocketDisconnect:
        await unsubscribe_ws(channel, websocket)


@router.post("/webhooks")
async def api_register_webhook(
    url: str = Query(...),
    events: str | None = Query(None, description="Comma-separated event types"),
    secret: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        event_list = events.split(",") if events else None
        sub = await register_webhook(db, user, url, event_list, secret)
        return {"id": sub.id, "url": sub.url, "events": event_list}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/webhooks")
async def api_list_webhooks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return {"webhooks": await list_webhooks(db, user)}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/webhooks/{webhook_id}")
async def api_delete_webhook(
    webhook_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_webhook(db, user, webhook_id)
        return {"deleted": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/logs")
async def api_event_logs(
    page: int = Query(1, ge=1),
    event_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await list_event_logs(db, page, event_type)

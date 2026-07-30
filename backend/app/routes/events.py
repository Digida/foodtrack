import json

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
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


class PublishEventRequest(BaseModel):
    event_type: str
    channel: str
    payload: dict = {}


class RegisterWebhookRequest(BaseModel):
    url: str
    events: str | None = None
    secret: str | None = None


@router.post("/publish")
async def api_publish_event(
    req: PublishEventRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await publish_event(db, user, req.event_type, req.channel, req.payload)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.websocket("/ws/{channel}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str,
    token: str | None = Query(None),
):
    """Authenticated WebSocket channel. Pass ?token=<jwt> as a query parameter."""
    from app.services.auth_service import decode_access_token
    from sqlalchemy import select
    from app.database import async_session

    if not token:
        await websocket.close(code=4001)
        return

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        await websocket.close(code=4001)
        return

    # Verify user exists and is active
    async with async_session() as db:
        from app.models.user import User as UserModel
        result = await db.execute(
            select(UserModel).where(UserModel.id == int(payload["sub"]))
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            await websocket.close(code=4001)
            return

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
    req: RegisterWebhookRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        event_list = req.events.split(",") if req.events else None
        sub = await register_webhook(db, user, req.url, event_list, req.secret)
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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_event_logs(db, page, event_type)

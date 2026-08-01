from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.contact import ContactMessage
from app.models.user import User
from app.utils.dependencies import require_admin

router = APIRouter(tags=["contact"])


class ContactForm(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str


class ContactResponse(BaseModel):
    success: bool
    message: str = "Message received. We will get back to you shortly."


@router.get("/contact/messages", response_model=list[dict])
async def get_contact_messages(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ContactMessage).order_by(ContactMessage.created_at.desc())
    )
    return [
        {
            "id": m.id,
            "name": m.name,
            "email": m.email,
            "subject": m.subject,
            "message": m.message,
            "created_at": m.created_at.isoformat(),
        }
        for m in result.scalars().all()
    ]


@router.post("/contact", response_model=ContactResponse)
async def submit_contact(form: ContactForm, db: AsyncSession = Depends(get_db)):
    msg = ContactMessage(
        name=form.name,
        email=form.email,
        subject=form.subject,
        message=form.message,
    )
    db.add(msg)
    await db.commit()
    return ContactResponse(success=True)

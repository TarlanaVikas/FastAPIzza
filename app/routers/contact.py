"""The contact form: anyone can write to the restaurant, staff read the inbox."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from ..models import ContactMessage
from ..ratelimit import RateLimiter
from ..schemas import ContactCreate, ContactOut
from ..security import DbSession, StaffUser

router = APIRouter(prefix="/contact", tags=["contact"])

contact_limiter = RateLimiter(5, 3600, "You've sent several messages already. Try again later.")


@router.post("/", status_code=status.HTTP_201_CREATED)
def send_message(payload: ContactCreate, request: Request, db: DbSession):
    # Bots tend to fill every field. Pretend it worked, store nothing.
    if payload.website:
        return {"detail": "Message sent."}
    contact_limiter.hit(request.client.host if request.client else "unknown")
    db.add(ContactMessage(name=payload.name, email=payload.email, message=payload.message))
    db.commit()
    return {"detail": "Message sent."}


@router.get("/", response_model=list[ContactOut])
def list_messages(_staff: StaffUser, db: DbSession):
    return db.scalars(select(ContactMessage).order_by(ContactMessage.created_at.desc(), ContactMessage.id.desc())).all()


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(message_id: int, _staff: StaffUser, db: DbSession):
    message = db.get(ContactMessage, message_id)
    if message is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found.")
    db.delete(message)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

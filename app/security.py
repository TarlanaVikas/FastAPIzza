"""JWT creation/verification and the authentication dependencies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User

settings = get_settings()
_bearer = HTTPBearer(auto_error=False)

TokenKind = Literal["access", "refresh"]


def create_token(user_id: int, kind: TokenKind) -> str:
    lifetime = (
        timedelta(minutes=settings.access_token_minutes)
        if kind == "access"
        else timedelta(days=settings.refresh_token_days)
    )
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "type": kind, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"}
    )


def decode_token(token: str, kind: TokenKind) -> int:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Your session has expired. Log in again.") from None
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid token.") from None
    if payload.get("type") != kind:
        raise _unauthorized("Invalid token.")
    try:
        return int(payload["sub"])
    except (TypeError, ValueError):
        raise _unauthorized("Invalid token.") from None


def _user_from_credentials(
    credentials: HTTPAuthorizationCredentials | None, db: Session, kind: TokenKind
) -> User:
    if credentials is None:
        raise _unauthorized("Not authenticated.")
    user = db.get(User, decode_token(credentials.credentials, kind))
    if user is None:
        raise _unauthorized("Invalid token.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled.")
    return user


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    return _user_from_credentials(credentials, db, "access")


def get_user_from_refresh_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    return _user_from_credentials(credentials, db, "refresh")


def require_staff(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_staff:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff access is required.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
StaffUser = Annotated[User, Depends(require_staff)]
DbSession = Annotated[Session, Depends(get_db)]

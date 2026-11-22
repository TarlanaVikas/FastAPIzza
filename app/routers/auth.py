"""Accounts: sign up, log in, token refresh and the signed-in user's profile."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from ..models import Order, User
from ..ratelimit import RateLimiter
from ..schemas import (
    USERNAME_PATTERN,
    AccessTokenResponse,
    LoginRequest,
    ProfileOut,
    ProfileUpdate,
    TokenResponse,
    UserListItem,
    UserOut,
    UserStats,
)
from ..security import (
    CurrentUser,
    DbSession,
    StaffUser,
    create_token,
    get_user_from_refresh_token,
)
from ..uploads import delete_image, has_file, save_image

router = APIRouter(prefix="/auth", tags=["auth"])

login_limiter = RateLimiter(10, 300, "Too many login attempts. Try again in a few minutes.")
signup_limiter = RateLimiter(10, 3600, "Too many sign-ups from this address. Try again later.")

# Checked when the username is unknown, so response time does not reveal which usernames exist.
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _find_by_username(db, username: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.username) == username.lower()))


def _find_by_email(db, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def _stats_for(db, user: User) -> UserStats:
    orders_count, pizzas, spent = db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.quantity), 0),
            func.coalesce(func.sum(Order.quantity * Order.unit_price), 0.0),
        ).where(Order.user_id == user.id)
    ).one()
    return UserStats(orders_count=orders_count, pizzas_ordered=int(pizzas), total_spent=round(float(spent), 2))


def _profile(db, user: User) -> ProfileOut:
    return ProfileOut(**UserOut.model_validate(user).model_dump(), stats=_stats_for(db, user))


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(
    request: Request,
    db: DbSession,
    username: Annotated[str, Form(pattern=USERNAME_PATTERN)],
    name: Annotated[str, Form(min_length=1, max_length=100)],
    email: Annotated[str, Form(max_length=120)],
    password: Annotated[str, Form(min_length=8, max_length=128)],
    image: Annotated[UploadFile | None, File()] = None,
):
    """Create a customer account. Staff accounts can only be created by an operator."""
    signup_limiter.hit(_client_key(request))
    username, name, email = username.strip(), name.strip(), email.strip().lower()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Enter your name.")
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Enter a valid email address.")
    if _find_by_username(db, username):
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is already taken.")
    if _find_by_email(db, email):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists.")

    stored_image = save_image(image) if has_file(image) else None
    user = User(
        username=username,
        name=name,
        email=email,
        password=generate_password_hash(password),
        is_staff=False,
        is_active=True,
        image=stored_image,
    )
    db.add(user)
    db.commit()
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: DbSession):
    key = f"{_client_key(request)}:{payload.username.lower()}"
    login_limiter.hit(key)
    user = _find_by_username(db, payload.username.strip())
    password_ok = check_password_hash(user.password if user else _DUMMY_HASH, payload.password)
    if not user or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled.")
    login_limiter.reset(key)
    return TokenResponse(
        access=create_token(user.id, "access"),
        refresh=create_token(user.id, "refresh"),
        is_staff=user.is_staff,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(user: Annotated[User, Depends(get_user_from_refresh_token)]):
    """Exchange a refresh token (sent as the Bearer token) for a new access token."""
    return AccessTokenResponse(access=create_token(user.id, "access"))


@router.get("/user", response_model=ProfileOut)
def get_profile(user: CurrentUser, db: DbSession):
    return _profile(db, user)


@router.put("/user", response_model=ProfileOut)
def update_profile(payload: ProfileUpdate, user: CurrentUser, db: DbSession):
    if payload.username and payload.username.lower() != user.username.lower():
        if _find_by_username(db, payload.username):
            raise HTTPException(status.HTTP_409_CONFLICT, "That username is already taken.")
    if payload.email and payload.email.lower() != user.email.lower():
        if _find_by_email(db, payload.email):
            raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists.")
    if payload.name is not None:
        user.name = payload.name
    if payload.username is not None:
        user.username = payload.username
    if payload.email is not None:
        user.email = payload.email.lower()
    db.commit()
    return _profile(db, user)


@router.post("/user/avatar", response_model=UserOut)
def upload_avatar(user: CurrentUser, db: DbSession, avatar: Annotated[UploadFile, File()]):
    new_image = save_image(avatar)
    old_image, user.image = user.image, new_image
    db.commit()
    delete_image(old_image)
    return user


@router.get("/users", response_model=list[UserListItem])
def list_users(_staff: StaffUser, db: DbSession):
    counts = dict(db.execute(select(Order.user_id, func.count(Order.id)).group_by(Order.user_id)).all())
    users = db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc())).all()
    return [
        UserListItem(**UserOut.model_validate(u).model_dump(), orders_count=counts.get(u.id, 0))
        for u in users
    ]

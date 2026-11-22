"""Pydantic request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from .models import OrderStatus, PizzaSize
from .uploads import public_url

USERNAME_PATTERN = r"^[A-Za-z0-9_.-]{3,25}$"

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Username = Annotated[str, StringConstraints(strip_whitespace=True, pattern=USERNAME_PATTERN)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Users -----------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access: str
    refresh: str
    token_type: str = "bearer"
    is_staff: bool


class AccessTokenResponse(BaseModel):
    access: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: int
    name: str
    username: str
    email: str
    is_staff: bool
    is_active: bool
    image: str | None = None
    created_at: datetime | None = None

    @field_validator("image")
    @classmethod
    def _image_url(cls, value: str | None) -> str | None:
        return public_url(value)


class UserStats(BaseModel):
    orders_count: int
    pizzas_ordered: int
    total_spent: float


class ProfileOut(UserOut):
    stats: UserStats


class UserListItem(UserOut):
    orders_count: int = 0


class ProfileUpdate(BaseModel):
    name: Name | None = None
    username: Username | None = None
    email: EmailStr | None = None


# ---- Pizzas ----------------------------------------------------------------
class PizzaOut(ORMModel):
    id: int
    name: str
    description: str
    image_url: str | None = None
    price: float

    @field_validator("image_url")
    @classmethod
    def _image_url(cls, value: str | None) -> str | None:
        return public_url(value)


class SizeOut(BaseModel):
    code: PizzaSize
    label: str
    multiplier: float


# ---- Orders ----------------------------------------------------------------
class OrderCreate(BaseModel):
    pizza_id: int
    pizza_size: PizzaSize = PizzaSize.SMALL
    quantity: int = Field(default=1, ge=1, le=10)


class OrderUpdate(BaseModel):
    pizza_size: PizzaSize | None = None
    quantity: int | None = Field(default=None, ge=1, le=10)


class OrderStatusUpdate(BaseModel):
    order_status: OrderStatus


class OrderOut(ORMModel):
    id: int
    pizza_id: int | None
    pizza_name: str
    pizza_image: str | None = None
    pizza_size: str
    quantity: int
    unit_price: float
    total: float
    order_status: str
    created_at: datetime
    updated_at: datetime

    @field_validator("pizza_image")
    @classmethod
    def _image_url(cls, value: str | None) -> str | None:
        return public_url(value)


class OrderCustomer(ORMModel):
    id: int
    name: str
    username: str


class AdminOrderOut(OrderOut):
    customer: OrderCustomer


# ---- Contact ---------------------------------------------------------------
class ContactCreate(BaseModel):
    name: Name
    email: EmailStr
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=2000)]
    website: str = ""  # honeypot: real visitors never see or fill this in


class ContactOut(ORMModel):
    id: int
    name: str
    email: str
    message: str
    created_at: datetime

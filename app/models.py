"""Database models and the small domain vocabulary (sizes, statuses, pricing)."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Always store UTC and always hand back timezone-aware values (SQLite drops the zone)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_TRANSIT = "IN-TRANSIT"
    DELIVERED = "DELIVERED"


class PizzaSize(str, enum.Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"
    EXTRA_LARGE = "EXTRA-LARGE"


# Price of a size relative to the pizza's listed (small) price.
SIZE_MULTIPLIERS: dict[PizzaSize, float] = {
    PizzaSize.SMALL: 1.0,
    PizzaSize.MEDIUM: 1.5,
    PizzaSize.LARGE: 2.0,
    PizzaSize.EXTRA_LARGE: 2.5,
}

SIZE_LABELS: dict[PizzaSize, str] = {
    PizzaSize.SMALL: "Small",
    PizzaSize.MEDIUM: "Medium",
    PizzaSize.LARGE: "Large",
    PizzaSize.EXTRA_LARGE: "Extra large",
}


def unit_price_for(base_price: float, size: PizzaSize) -> float:
    return round(base_price * SIZE_MULTIPLIERS[size], 2)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(25), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(Text, nullable=False)  # salted hash, never plain text
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    image: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    orders: Mapped[list["Order"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Pizza(Base):
    __tablename__ = "pizzas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    image_url: Mapped[str | None] = mapped_column(String(200))
    price: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    def __repr__(self) -> str:
        return f"<Pizza {self.name}>"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # The pizza may be removed from the menu later, so its name and unit price are kept on the order.
    pizza_id: Mapped[int | None] = mapped_column(ForeignKey("pizzas.id", ondelete="SET NULL"))
    pizza_name: Mapped[str] = mapped_column(String(200), nullable=False)
    pizza_size: Mapped[str] = mapped_column(String(20), default=PizzaSize.SMALL.value, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    order_status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="orders")
    pizza: Mapped[Pizza | None] = relationship()

    @property
    def total(self) -> float:
        return round(self.unit_price * self.quantity, 2)

    @property
    def pizza_image(self) -> str | None:
        return self.pizza.image_url if self.pizza else None

    @property
    def customer(self) -> User:
        return self.user

    def __repr__(self) -> str:
        return f"<Order {self.id}>"


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

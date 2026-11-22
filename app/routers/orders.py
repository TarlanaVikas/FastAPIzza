"""Orders: customers manage their own, staff see and progress everyone's."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ..models import Order, OrderStatus, Pizza, unit_price_for, PizzaSize
from ..schemas import AdminOrderOut, OrderCreate, OrderOut, OrderStatusUpdate, OrderUpdate
from ..security import CurrentUser, DbSession, StaffUser

router = APIRouter(prefix="/orders", tags=["orders"])


def _get_or_404(db, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found.")
    return order


def _get_owned(db, order_id: int, user) -> Order:
    order = _get_or_404(db, order_id)
    # Report someone else's order as missing so ids cannot be probed.
    if order.user_id != user.id and not user.is_staff:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found.")
    return order


@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(payload: OrderCreate, user: CurrentUser, db: DbSession):
    pizza = db.get(Pizza, payload.pizza_id)
    if pizza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That pizza is no longer on the menu.")
    order = Order(
        user_id=user.id,
        pizza_id=pizza.id,
        pizza_name=pizza.name,
        pizza_size=payload.pizza_size.value,
        quantity=payload.quantity,
        unit_price=unit_price_for(pizza.price, payload.pizza_size),
        order_status=OrderStatus.PENDING.value,
    )
    db.add(order)
    db.commit()
    return order


@router.get("/mine", response_model=list[OrderOut])
def my_orders(user: CurrentUser, db: DbSession):
    return db.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .options(joinedload(Order.pizza))
        .order_by(Order.created_at.desc(), Order.id.desc())
    ).all()


@router.get("/", response_model=list[AdminOrderOut])
def all_orders(
    _staff: StaffUser,
    db: DbSession,
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
):
    query = (
        select(Order)
        .options(joinedload(Order.user), joinedload(Order.pizza))
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    if status_filter:
        query = query.where(Order.order_status == status_filter.value)
    return db.scalars(query).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, user: CurrentUser, db: DbSession):
    return _get_owned(db, order_id, user)


@router.put("/{order_id}", response_model=OrderOut)
def update_order(order_id: int, payload: OrderUpdate, user: CurrentUser, db: DbSession):
    """Change size or quantity. Only the owner can do this, and only while the order is pending."""
    order = db.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found.")
    if order.order_status != OrderStatus.PENDING.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only pending orders can be changed.")
    if payload.pizza_size is not None and payload.pizza_size.value != order.pizza_size:
        if order.pizza is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "That pizza is no longer on the menu, so its size can't change.")
        order.pizza_size = payload.pizza_size.value
        order.unit_price = unit_price_for(order.pizza.price, PizzaSize(order.pizza_size))
    if payload.quantity is not None:
        order.quantity = payload.quantity
    db.commit()
    return order


@router.patch("/{order_id}/status", response_model=AdminOrderOut)
def update_status(order_id: int, payload: OrderStatusUpdate, _staff: StaffUser, db: DbSession):
    order = _get_or_404(db, order_id)
    order.order_status = payload.order_status.value
    db.commit()
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_order(order_id: int, user: CurrentUser, db: DbSession):
    """Customers can cancel their own pending orders; staff can remove any order."""
    order = _get_owned(db, order_id, user)
    if not user.is_staff and order.order_status != OrderStatus.PENDING.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only pending orders can be cancelled.")
    db.delete(order)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

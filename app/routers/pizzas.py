"""The menu: public browsing, staff-only management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select

from ..models import SIZE_LABELS, SIZE_MULTIPLIERS, Pizza
from ..schemas import PizzaOut, SizeOut
from ..security import DbSession, StaffUser
from ..uploads import delete_image, has_file, save_image

router = APIRouter(prefix="/pizzas", tags=["pizzas"])

NameField = Annotated[str, Form(min_length=1, max_length=200)]
DescriptionField = Annotated[str, Form(max_length=500)]
PriceField = Annotated[float, Form(gt=0, le=100000)]


def _get_or_404(db, pizza_id: int) -> Pizza:
    pizza = db.get(Pizza, pizza_id)
    if pizza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pizza not found.")
    return pizza


@router.get("/sizes", response_model=list[SizeOut])
def list_sizes():
    return [SizeOut(code=size, label=SIZE_LABELS[size], multiplier=mult) for size, mult in SIZE_MULTIPLIERS.items()]


@router.get("/", response_model=list[PizzaOut])
def list_pizzas(
    db: DbSession,
    search: Annotated[str | None, Query(max_length=100, description="Filter by name")] = None,
):
    query = select(Pizza).order_by(Pizza.id)
    if search and search.strip():
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Pizza.name.ilike(f"%{escaped}%", escape="\\"))
    return db.scalars(query).all()


@router.get("/{pizza_id}", response_model=PizzaOut)
def get_pizza(pizza_id: int, db: DbSession):
    return _get_or_404(db, pizza_id)


@router.post("/", response_model=PizzaOut, status_code=status.HTTP_201_CREATED)
def add_pizza(
    _staff: StaffUser,
    db: DbSession,
    name: NameField,
    price: PriceField,
    description: DescriptionField = "",
    image: Annotated[UploadFile | None, File()] = None,
):
    name = name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Enter a pizza name.")
    pizza = Pizza(
        name=name,
        description=description.strip(),
        price=round(price, 2),
        image_url=save_image(image) if has_file(image) else None,
    )
    db.add(pizza)
    db.commit()
    return pizza


@router.put("/{pizza_id}", response_model=PizzaOut)
def update_pizza(
    pizza_id: int,
    _staff: StaffUser,
    db: DbSession,
    name: Annotated[str | None, Form(min_length=1, max_length=200)] = None,
    description: DescriptionField | None = None,
    price: Annotated[float | None, Form(gt=0, le=100000)] = None,
    image: Annotated[UploadFile | None, File()] = None,
):
    pizza = _get_or_404(db, pizza_id)
    if name is not None:
        if not name.strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Enter a pizza name.")
        pizza.name = name.strip()
    if description is not None:
        pizza.description = description.strip()
    if price is not None:
        pizza.price = round(price, 2)
    old_image = None
    if has_file(image):
        old_image, pizza.image_url = pizza.image_url, save_image(image)
    db.commit()
    delete_image(old_image)
    return pizza


@router.delete("/{pizza_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pizza(pizza_id: int, _staff: StaffUser, db: DbSession):
    pizza = _get_or_404(db, pizza_id)
    image = pizza.image_url
    db.delete(pizza)
    db.commit()
    delete_image(image)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

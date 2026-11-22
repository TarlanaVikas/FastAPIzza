"""Create the database tables and, optionally, a starter menu.

    python -m scripts.init_db            # tables only
    python -m scripts.init_db --seed     # tables + starter pizzas missing from the menu
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Pizza

STARTER_MENU = [
    ("Margherita", "Tomato, fresh mozzarella and basil on a blistered crust.", 100.0, "/static/img/pizza-margherita.svg"),
    ("Pepperoni", "Mozzarella, tomato sauce and crisp-edged pepperoni.", 120.0, "/static/img/pizza-pepperoni.svg"),
    ("Veggie Garden", "Peppers, olives, mushrooms and red onion over mozzarella.", 110.0, "/static/img/pizza-veggie.svg"),
    ("Hawaiian", "Tomato sauce, ham, pineapple and mozzarella.", 125.0, None),
    ("BBQ Chicken", "Smoky barbecue sauce, chicken, red onion and mozzarella.", 135.0, None),
    ("Meat Lovers", "Pepperoni, sausage, ham and mozzarella.", 145.0, None),
    ("Four Cheese", "Mozzarella, parmesan, gorgonzola and cheddar.", 140.0, None),
    ("Mushroom Supreme", "Mushrooms, olives, peppers and mozzarella.", 130.0, None),
    ("Spicy Diablo", "Pepperoni, jalapenos, chili flakes and hot tomato sauce.", 135.0, None),
    ("Pesto & Tomato", "Basil pesto, cherry tomatoes and fresh mozzarella.", 138.0, None),
]


def seed_menu() -> int:
    with SessionLocal() as db:
        existing_names = {
            name.lower()
            for name in db.scalars(select(Pizza.name)).all()
        }
        added = 0
        for name, description, price, image in STARTER_MENU:
            if name.lower() in existing_names:
                continue
            db.add(Pizza(name=name, description=description, price=price, image_url=image))
            existing_names.add(name.lower())
            added += 1
        db.commit()
        return added


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", action="store_true", help="add a starter menu when the menu is empty")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    print("Tables ready.")
    if args.seed:
        added = seed_menu()
        print(f"Added {added} starter pizzas." if added else "Menu already has pizzas; nothing added.")


if __name__ == "__main__":
    main()

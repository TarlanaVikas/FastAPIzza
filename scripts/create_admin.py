"""Create a staff account, or promote an existing user to staff.

Staff accounts cannot be created from the public sign-up form, by design.

    python -m scripts.create_admin

Values come from ADMIN_USERNAME, ADMIN_NAME, ADMIN_EMAIL and ADMIN_PASSWORD when set,
otherwise you are prompted (the password prompt does not echo).
"""

from __future__ import annotations

import getpass
import os
import re
import sys

from sqlalchemy import func, select
from werkzeug.security import generate_password_hash

from app.database import Base, SessionLocal, engine
from app.models import User
from app.schemas import USERNAME_PATTERN


def _value(env_name: str, prompt: str, secret: bool = False) -> str:
    value = os.getenv(env_name, "").strip()
    if value:
        return value
    return (getpass.getpass(prompt) if secret else input(prompt)).strip()


def main() -> int:
    Base.metadata.create_all(bind=engine)
    username = _value("ADMIN_USERNAME", "Username: ")
    if not re.match(USERNAME_PATTERN, username):
        print("Username must be 3-25 characters: letters, numbers, dot, dash or underscore.")
        return 1

    with SessionLocal() as db:
        existing = db.scalar(select(User).where(func.lower(User.username) == username.lower()))
        if existing:
            existing.is_staff = True
            existing.is_active = True
            db.commit()
            print(f"'{existing.username}' already existed and is now staff.")
            return 0

        name = _value("ADMIN_NAME", "Full name: ")
        email = _value("ADMIN_EMAIL", "Email: ").lower()
        password = _value("ADMIN_PASSWORD", "Password (min 8 characters): ", secret=True)
        if not name or "@" not in email:
            print("A name and a valid email are required.")
            return 1
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            return 1
        if db.scalar(select(User).where(func.lower(User.email) == email)):
            print("A user with that email already exists.")
            return 1

        db.add(User(name=name, username=username, email=email, password=generate_password_hash(password), is_staff=True))
        db.commit()
        print(f"Staff account '{username}' created.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

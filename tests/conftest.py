import os
import tempfile
from pathlib import Path

# Configure the app before it is imported: temporary database and upload folder.
_TMP = tempfile.mkdtemp(prefix="fastapizza-tests-")
# Set TEST_DATABASE_URL to run the suite against another database (for example PostgreSQL).
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{Path(_TMP) / 'test.db'}"
os.environ["UPLOAD_DIR"] = str(Path(_TMP) / "upload")
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256-use"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Pizza, User  # noqa: E402
from app.routers import auth as auth_router  # noqa: E402
from app.routers import contact as contact_router  # noqa: E402

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    for limiter in (auth_router.login_limiter, auth_router.signup_limiter, contact_router.contact_limiter):
        limiter.reset()
    yield


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def signup(client, username="mario", email="mario@example.com", password="correct-horse", name="Mario Rossi", **extra):
    data = {"username": username, "email": email, "password": password, "name": name, **extra}
    return client.post("/auth/signup", data=data)


def login(client, username="mario", password="correct-horse"):
    return client.post("/auth/login", json={"username": username, "password": password})


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def customer(client):
    assert signup(client).status_code == 201
    tokens = login(client).json()
    return {"headers": auth_header(tokens["access"]), "tokens": tokens}


@pytest.fixture()
def staff(client):
    with SessionLocal() as db:
        db.add(User(name="Chef", username="chef", email="chef@example.com",
                    password=generate_password_hash("kitchen-pass"), is_staff=True))
        db.commit()
    tokens = login(client, "chef", "kitchen-pass").json()
    return {"headers": auth_header(tokens["access"]), "tokens": tokens}


@pytest.fixture()
def pizza():
    with SessionLocal() as db:
        item = Pizza(name="Margherita", description="Tomato and basil", price=100.0)
        db.add(item)
        db.commit()
        return item.id

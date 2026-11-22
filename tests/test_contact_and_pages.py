import pytest

from .conftest import auth_header


def test_contact_flow(client, staff):
    payload = {"name": "Ada", "email": "ada@example.com", "message": "Do you do gluten-free bases?"}
    assert client.post("/contact/", json=payload).status_code == 201
    assert client.get("/contact/").status_code == 401
    messages = client.get("/contact/", headers=staff["headers"]).json()
    assert len(messages) == 1 and messages[0]["name"] == "Ada"
    assert client.delete(f"/contact/{messages[0]['id']}", headers=staff["headers"]).status_code == 204
    assert client.get("/contact/", headers=staff["headers"]).json() == []


def test_contact_validation_honeypot_and_rate_limit(client, staff):
    assert client.post("/contact/", json={"name": "A", "email": "nope", "message": "hello there"}).status_code == 422
    # Honeypot: looks successful, stores nothing.
    bot = {"name": "Bot", "email": "bot@example.com", "message": "buy stuff now", "website": "http://spam"}
    assert client.post("/contact/", json=bot).status_code == 201
    assert client.get("/contact/", headers=staff["headers"]).json() == []
    ok = {"name": "Ada", "email": "ada@example.com", "message": "Hello hello"}
    codes = [client.post("/contact/", json=ok).status_code for _ in range(6)]
    assert codes == [201] * 5 + [429]


def test_customer_cannot_read_inbox(client, customer):
    assert client.get("/contact/", headers=customer["headers"]).status_code == 403


PAGES = [
    "/", "/auth/login", "/auth/signup", "/user/dashboard", "/user/place-order", "/user/order-data",
    "/user/contact", "/user/profile", "/admin/dashboard", "/admin/orders", "/admin/users",
    "/admin/messages", "/admin/profile",
]


@pytest.mark.parametrize("path", PAGES)
def test_pages_render_with_branding(client, path):
    res = client.get(path)
    assert res.status_code == 200
    assert "FastAPIzza" in res.text
    assert "<title>" in res.text and 'rel="icon"' in res.text
    assert "script-src 'self'" in res.headers["content-security-policy"]


@pytest.mark.parametrize("path", PAGES)
def test_pages_have_no_inline_scripts_or_handlers(client, path):
    text = client.get(path).text
    assert "<script>" not in text
    assert " onclick=" not in text and " style=" not in text


def test_html_404_and_json_404(client):
    html = client.get("/nope", headers={"accept": "text/html"})
    assert html.status_code == 404 and "FastAPIzza" in html.text and "on the menu." in html.text
    api = client.get("/nope", headers={"accept": "application/json"})
    assert api.status_code == 404 and api.json() == {"detail": "Not Found"}


def test_security_headers_and_health(client):
    res = client.get("/health")
    assert res.json() == {"status": "ok"}
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" not in client.get("/docs").headers


def test_static_assets_are_served(client):
    for path in ["/static/css/fastapizza.css", "/static/js/core.js", "/static/img/favicon.svg", "/static/img/pizza-margherita.svg"]:
        assert client.get(path).status_code == 200, path

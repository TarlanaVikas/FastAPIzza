from .conftest import PNG_BYTES, auth_header, login, signup


def test_signup_returns_user_without_password(client):
    res = signup(client)
    assert res.status_code == 201
    body = res.json()
    assert body["username"] == "mario" and body["is_staff"] is False
    assert "password" not in body


def test_signup_cannot_create_staff(client):
    res = signup(client, is_staff="true")
    assert res.status_code == 201
    assert res.json()["is_staff"] is False
    token = login(client).json()
    assert token["is_staff"] is False
    assert client.get("/auth/users", headers=auth_header(token["access"])).status_code == 403


def test_signup_rejects_duplicates_case_insensitively(client):
    assert signup(client).status_code == 201
    assert signup(client, username="MARIO", email="other@example.com").status_code == 409
    assert signup(client, username="luigi", email="MARIO@example.com").status_code == 409


def test_signup_validation(client):
    assert signup(client, password="short").status_code == 422
    assert signup(client, username="a b").status_code == 422
    assert signup(client, email="not-an-email").status_code == 422


def test_signup_with_avatar_and_rejects_non_images(client):
    ok = client.post(
        "/auth/signup",
        data={"username": "pic", "email": "pic@example.com", "password": "correct-horse", "name": "Pic"},
        files={"image": ("me.png", PNG_BYTES, "image/png")},
    )
    assert ok.status_code == 201
    assert ok.json()["image"].startswith("/upload/") and ok.json()["image"].endswith(".png")
    assert client.get(ok.json()["image"]).status_code == 200

    bad = client.post(
        "/auth/signup",
        data={"username": "evil", "email": "evil@example.com", "password": "correct-horse", "name": "Evil"},
        files={"image": ("x.png", b"<svg onload=alert(1)>", "image/png")},
    )
    assert bad.status_code == 415


def test_login_success_and_failure(client):
    signup(client)
    ok = login(client)
    assert ok.status_code == 200
    assert {"access", "refresh", "is_staff"} <= ok.json().keys()
    assert login(client, password="wrong-password").status_code == 401
    assert login(client, username="nobody").status_code == 401


def test_login_is_case_insensitive_on_username(client):
    signup(client)
    assert login(client, username="MARIO").status_code == 200


def test_login_rate_limited(client):
    signup(client)
    codes = [login(client, password="nope-nope").status_code for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429


def test_protected_routes_need_a_token(client):
    assert client.get("/auth/user").status_code == 401
    assert client.get("/auth/user", headers=auth_header("garbage")).status_code == 401


def test_refresh_token_flow(client):
    signup(client)
    tokens = login(client).json()
    # A refresh token cannot be used as an access token, and vice versa.
    assert client.get("/auth/user", headers=auth_header(tokens["refresh"])).status_code == 401
    assert client.post("/auth/refresh", headers=auth_header(tokens["access"])).status_code == 401
    fresh = client.post("/auth/refresh", headers=auth_header(tokens["refresh"]))
    assert fresh.status_code == 200
    assert client.get("/auth/user", headers=auth_header(fresh.json()["access"])).status_code == 200


def test_profile_read_update_and_stats(client, customer):
    res = client.get("/auth/user", headers=customer["headers"])
    assert res.status_code == 200
    assert res.json()["stats"] == {"orders_count": 0, "pizzas_ordered": 0, "total_spent": 0.0}

    upd = client.put("/auth/user", headers=customer["headers"], json={"name": "Mario R.", "email": "m@example.com"})
    assert upd.status_code == 200 and upd.json()["name"] == "Mario R."


def test_profile_update_rejects_taken_username(client, customer):
    signup(client, username="luigi", email="luigi@example.com")
    res = client.put("/auth/user", headers=customer["headers"], json={"username": "luigi"})
    assert res.status_code == 409


def test_token_survives_username_change(client, customer):
    client.put("/auth/user", headers=customer["headers"], json={"username": "mario2"})
    assert client.get("/auth/user", headers=customer["headers"]).json()["username"] == "mario2"


def test_avatar_upload_replaces_old_file(client, customer):
    first = client.post("/auth/user/avatar", headers=customer["headers"], files={"avatar": ("a.png", PNG_BYTES, "image/png")})
    assert first.status_code == 200
    old = first.json()["image"]
    second = client.post("/auth/user/avatar", headers=customer["headers"], files={"avatar": ("b.png", PNG_BYTES, "image/png")})
    assert second.json()["image"] != old
    assert client.get(old).status_code == 404


def test_staff_user_list_includes_order_counts(client, staff, customer, pizza):
    client.post("/orders/", headers=customer["headers"], json={"pizza_id": pizza, "quantity": 2})
    users = client.get("/auth/users", headers=staff["headers"]).json()
    mario = next(u for u in users if u["username"] == "mario")
    assert mario["orders_count"] == 1 and "password" not in mario

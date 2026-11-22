from .conftest import PNG_BYTES, auth_header, signup, login


def test_menu_is_public_and_searchable(client, pizza):
    assert client.get("/pizzas/").json()[0]["name"] == "Margherita"
    assert len(client.get("/pizzas/", params={"search": "marg"}).json()) == 1
    assert client.get("/pizzas/", params={"search": "zzz"}).json() == []
    assert client.get("/pizzas/", params={"search": "%"}).json() == []  # wildcard is escaped, not expanded
    assert client.get(f"/pizzas/{pizza}").status_code == 200
    assert client.get("/pizzas/9999").status_code == 404


def test_sizes_endpoint(client):
    sizes = client.get("/pizzas/sizes").json()
    assert [s["code"] for s in sizes] == ["SMALL", "MEDIUM", "LARGE", "EXTRA-LARGE"]


def test_only_staff_can_manage_menu(client, customer, staff):
    form = {"name": "Funghi", "price": "130", "description": "Mushrooms"}
    assert client.post("/pizzas/", data=form).status_code == 401
    assert client.post("/pizzas/", data=form, headers=customer["headers"]).status_code == 403
    created = client.post("/pizzas/", data=form, headers=staff["headers"], files={"image": ("p.png", PNG_BYTES, "image/png")})
    assert created.status_code == 201
    pid = created.json()["id"]
    assert created.json()["image_url"].startswith("/upload/")

    assert client.put(f"/pizzas/{pid}", data={"price": "99"}, headers=customer["headers"]).status_code == 403
    assert client.delete(f"/pizzas/{pid}", headers=customer["headers"]).status_code == 403

    upd = client.put(f"/pizzas/{pid}", data={"price": "150.5", "name": "Funghi Bianca"}, headers=staff["headers"])
    assert upd.status_code == 200 and upd.json()["price"] == 150.5 and upd.json()["name"] == "Funghi Bianca"

    image = created.json()["image_url"]
    assert client.delete(f"/pizzas/{pid}", headers=staff["headers"]).status_code == 204
    assert client.get(f"/pizzas/{pid}").status_code == 404
    assert client.get(image).status_code == 404  # the stored image is removed with the pizza


def test_add_pizza_validation(client, staff):
    assert client.post("/pizzas/", data={"name": "X", "price": "-5"}, headers=staff["headers"]).status_code == 422
    assert client.post("/pizzas/", data={"name": "X", "price": "abc"}, headers=staff["headers"]).status_code == 422
    bad = client.post("/pizzas/", data={"name": "X", "price": "10"}, headers=staff["headers"],
                      files={"image": ("a.png", b"not an image", "image/png")})
    assert bad.status_code == 415


def test_order_flow_and_pricing(client, customer, pizza):
    res = client.post("/orders/", headers=customer["headers"], json={"pizza_id": pizza, "pizza_size": "LARGE", "quantity": 3})
    assert res.status_code == 201
    order = res.json()
    assert order["order_status"] == "PENDING" and order["unit_price"] == 200.0 and order["total"] == 600.0
    assert order["pizza_name"] == "Margherita"

    mine = client.get("/orders/mine", headers=customer["headers"]).json()
    assert [o["id"] for o in mine] == [order["id"]]
    assert client.get(f"/orders/{order['id']}", headers=customer["headers"]).status_code == 200


def test_order_validation(client, customer, pizza):
    h = customer["headers"]
    assert client.post("/orders/", headers=h, json={"pizza_id": pizza, "quantity": 0}).status_code == 422
    assert client.post("/orders/", headers=h, json={"pizza_id": pizza, "quantity": 99}).status_code == 422
    assert client.post("/orders/", headers=h, json={"pizza_id": pizza, "pizza_size": "HUGE"}).status_code == 422
    assert client.post("/orders/", headers=h, json={"pizza_id": 9999}).status_code == 404
    assert client.post("/orders/", json={"pizza_id": pizza}).status_code == 401


def test_customers_cannot_touch_each_others_orders(client, customer, pizza):
    order = client.post("/orders/", headers=customer["headers"], json={"pizza_id": pizza}).json()
    signup(client, username="luigi", email="luigi@example.com")
    other = auth_header(login(client, "luigi").json()["access"])
    assert client.get(f"/orders/{order['id']}", headers=other).status_code == 404
    assert client.put(f"/orders/{order['id']}", headers=other, json={"quantity": 5}).status_code == 404
    assert client.delete(f"/orders/{order['id']}", headers=other).status_code == 404
    assert client.get("/orders/mine", headers=other).json() == []
    assert client.get("/orders/", headers=other).status_code == 403


def test_edit_and_cancel_only_while_pending(client, customer, staff, pizza):
    h = customer["headers"]
    oid = client.post("/orders/", headers=h, json={"pizza_id": pizza, "quantity": 1}).json()["id"]

    edited = client.put(f"/orders/{oid}", headers=h, json={"pizza_size": "MEDIUM", "quantity": 2})
    assert edited.status_code == 200 and edited.json()["total"] == 300.0

    assert client.patch(f"/orders/{oid}/status", headers=h, json={"order_status": "DELIVERED"}).status_code == 403
    moved = client.patch(f"/orders/{oid}/status", headers=staff["headers"], json={"order_status": "IN-TRANSIT"})
    assert moved.status_code == 200 and moved.json()["order_status"] == "IN-TRANSIT"
    assert moved.json()["customer"]["username"] == "mario"
    assert client.patch(f"/orders/{oid}/status", headers=staff["headers"], json={"order_status": "COOKED"}).status_code == 422

    assert client.put(f"/orders/{oid}", headers=h, json={"quantity": 5}).status_code == 409
    assert client.delete(f"/orders/{oid}", headers=h).status_code == 409

    pending = client.post("/orders/", headers=h, json={"pizza_id": pizza}).json()["id"]
    assert client.delete(f"/orders/{pending}", headers=h).status_code == 204
    assert client.get(f"/orders/{pending}", headers=h).status_code == 404


def test_staff_order_list_and_filter(client, customer, staff, pizza):
    first = client.post("/orders/", headers=customer["headers"], json={"pizza_id": pizza}).json()["id"]
    client.post("/orders/", headers=customer["headers"], json={"pizza_id": pizza})
    client.patch(f"/orders/{first}/status", headers=staff["headers"], json={"order_status": "DELIVERED"})
    assert len(client.get("/orders/", headers=staff["headers"]).json()) == 2
    delivered = client.get("/orders/", headers=staff["headers"], params={"status": "DELIVERED"}).json()
    assert [o["id"] for o in delivered] == [first]


def test_order_survives_pizza_deletion(client, customer, staff, pizza):
    h = customer["headers"]
    oid = client.post("/orders/", headers=h, json={"pizza_id": pizza, "pizza_size": "LARGE"}).json()["id"]
    assert client.delete(f"/pizzas/{pizza}", headers=staff["headers"]).status_code == 204
    order = client.get(f"/orders/{oid}", headers=h).json()
    assert order["pizza_name"] == "Margherita" and order["pizza_id"] is None and order["total"] == 200.0
    # Size can't be re-priced without the pizza, but quantity can still change.
    assert client.put(f"/orders/{oid}", headers=h, json={"pizza_size": "SMALL"}).status_code == 409
    assert client.put(f"/orders/{oid}", headers=h, json={"quantity": 2}).json()["total"] == 400.0


def test_profile_stats_reflect_orders(client, customer, pizza):
    h = customer["headers"]
    client.post("/orders/", headers=h, json={"pizza_id": pizza, "quantity": 2})
    client.post("/orders/", headers=h, json={"pizza_id": pizza, "pizza_size": "MEDIUM", "quantity": 1})
    stats = client.get("/auth/user", headers=h).json()["stats"]
    assert stats == {"orders_count": 2, "pizzas_ordered": 3, "total_spent": 350.0}


def test_timestamps_are_utc_aware(client, customer, pizza):
    order = client.post("/orders/", headers=customer["headers"], json={"pizza_id": pizza}).json()
    assert order["created_at"].endswith("Z") or order["created_at"].endswith("+00:00")

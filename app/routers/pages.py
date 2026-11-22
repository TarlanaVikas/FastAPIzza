"""HTML pages. Each one is a Jinja template; data is loaded by the page's own script via the JSON API."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import render

router = APIRouter(include_in_schema=False)

# path -> (template, shell, title, active nav item)
#   shell: "public" (marketing), "auth" (sign in/up), "app" (customer), "admin" (staff)
PAGES: dict[str, tuple[str, str, str, str]] = {
    "/": ("landing.html", "public", "Order pizza online", "home"),
    "/auth/login": ("login.html", "auth", "Log in", ""),
    "/auth/signup": ("register.html", "auth", "Create your account", ""),
    "/user/dashboard": ("dashboard.html", "app", "Menu", "menu"),
    "/user/place-order": ("place_order.html", "app", "Place an order", "menu"),
    "/user/order-data": ("orders.html", "app", "Your orders", "orders"),
    "/user/contact": ("contact.html", "app", "Contact", "contact"),
    "/user/profile": ("profile.html", "app", "Your profile", "profile"),
    "/admin/dashboard": ("admin_menu.html", "admin", "Menu management", "menu"),
    "/admin/orders": ("admin_orders.html", "admin", "Orders", "orders"),
    "/admin/users": ("admin_users.html", "admin", "Customers", "users"),
    "/admin/messages": ("admin_messages.html", "admin", "Messages", "messages"),
    "/admin/profile": ("profile.html", "admin", "Your profile", "profile"),
}


def _register(path: str, template: str, shell: str, title: str, active: str) -> None:
    async def page(request: Request) -> HTMLResponse:
        return render(request, template, shell=shell, title=title, active=active)

    page.__name__ = f"page_{path.strip('/').replace('/', '_') or 'home'}"
    router.add_api_route(path, page, methods=["GET"], response_class=HTMLResponse)


for _path, (_template, _shell, _title, _active) in PAGES.items():
    _register(_path, _template, _shell, _title, _active)

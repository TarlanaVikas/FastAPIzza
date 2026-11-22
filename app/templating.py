"""Shared Jinja2 environment."""

from __future__ import annotations

from fastapi import Request
from fastapi.templating import Jinja2Templates

from .config import BASE_DIR, get_settings

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["app_name"] = get_settings().app_name


def render(request: Request, template: str, status_code: int = 200, **context):
    return templates.TemplateResponse(request, template, context, status_code=status_code)

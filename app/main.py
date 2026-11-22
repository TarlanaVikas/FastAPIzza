"""FastAPIzza application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import BASE_DIR, get_settings
from .database import Base, engine
from .routers import auth, contact, orders, pages, pizzas
from .templating import render
from .uploads import ensure_upload_dir

settings = get_settings()

DESCRIPTION = "Order pizza from the FastAPIzza menu, and run the kitchen from the staff dashboard."

# Everything is served from this origin, so the page may only load its own scripts, styles and fonts.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_upload_dir()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, description=DESCRIPTION, version="1.0.0", lifespan=lifespan)

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(pizzas.router)
app.include_router(orders.router)
app.include_router(contact.router)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
ensure_upload_dir()
app.mount("/upload", StaticFiles(directory=settings.upload_dir), name="upload")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if not request.url.path.startswith(DOCS_PATHS):  # Swagger UI pulls assets from a CDN
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    return response


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse("/static/img/favicon.ico", status_code=301)


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


# ---- Error pages: HTML for browsers, JSON for API clients --------------------
def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


ERROR_COPY = {
    404: ("This page isn't on the menu.", "The link may be old, or the page may have moved."),
    403: ("This table is reserved.", "You don't have access to this page."),
    405: ("That isn't how this works.", "This address doesn't accept that kind of request."),
}


@app.exception_handler(StarletteHTTPException)
async def html_aware_http_exception(request: Request, exc: StarletteHTTPException):
    if _wants_html(request) and exc.status_code in ERROR_COPY:
        headline, detail = ERROR_COPY[exc.status_code]
        return render(
            request, "error.html", status_code=exc.status_code,
            shell="public", title=headline, active="", code=exc.status_code, headline=headline, detail=detail,
        )
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    import logging

    logging.getLogger("fastapizza").exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    if _wants_html(request):
        return render(
            request, "error.html", status_code=500,
            shell="public", title="Something burned", active="", code=500,
            headline="Something burned in the kitchen.",
            detail="It's our fault, not yours. Try again in a moment.",
        )
    return JSONResponse({"detail": "Internal server error."}, status_code=500)

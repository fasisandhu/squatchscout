import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import deps
from app.config import get_settings
from app.logging_setup import configure_logging
from app.routers import export, health, industries, intent, leads, searches
from app.services.housekeeping import run_daily


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(get_settings().log_level)
    stop = asyncio.Event()
    task = asyncio.create_task(run_daily(stop))
    yield
    stop.set()
    task.cancel()
    await deps.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    deps.reset_for_tests()
    app = FastAPI(title="SquatchScout API", version=settings.app_version, lifespan=lifespan)

    # Starlette pulls Exception/500 handlers out of ExceptionMiddleware and installs them on
    # ServerErrorMiddleware, which sits OUTSIDE every app.add_middleware(...) call (including
    # CORS below) — so @app.exception_handler(Exception) alone never gets a chance to have CORS
    # headers stamped onto its response. This plain HTTP middleware, registered before CORS is
    # added, sits INSIDE CORSMiddleware instead, so its JSONResponse still passes back out
    # through CORSMiddleware and picks up the Access-Control-Allow-Origin header (spec §9).
    @app.middleware("http")
    async def catch_unhandled_errors(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content={"error": {"code": "internal", "message": type(exc).__name__}},
            )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registered on Starlette's base HTTPException, not FastAPI's subclass: FastAPI's routing
    # itself (404s on unmatched paths, 405s on wrong methods) raises the Starlette base class
    # directly, so a handler keyed on the fastapi subclass never catches those. Routes still
    # raise fastapi.HTTPException — the MRO lookup finds this handler via its Starlette parent.
    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        detail = (
            exc.detail
            if isinstance(exc.detail, dict)
            else {"code": "http_error", "message": str(exc.detail)}
        )
        return JSONResponse(status_code=exc.status_code, content={"error": detail})

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):  # backstop only — see middleware above
        return JSONResponse(
            status_code=500, content={"error": {"code": "internal", "message": type(exc).__name__}}
        )

    for r in (health, industries, searches, leads, export, intent):
        app.include_router(r.router)
    return app


app = create_app()

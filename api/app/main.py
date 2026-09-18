from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import deps
from app.config import get_settings
from app.routers import health, industries, leads, searches


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await deps.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    deps.reset_for_tests()
    app = FastAPI(title="SquatchScout API", version=settings.app_version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        detail = (
            exc.detail
            if isinstance(exc.detail, dict)
            else {"code": "http_error", "message": str(exc.detail)}
        )
        return JSONResponse(status_code=exc.status_code, content={"error": detail})

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):  # keeps CORS headers on 500s (spec §9)
        return JSONResponse(
            status_code=500, content={"error": {"code": "internal", "message": type(exc).__name__}}
        )

    for r in (health, industries, searches, leads):
        app.include_router(r.router)
    return app


app = create_app()

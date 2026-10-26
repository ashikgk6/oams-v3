"""Application factory (Factory Method) — builds a configured FastAPI instance."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.bootstrap.lifecycle import ApplicationBootstrap
from app.config import Settings, get_settings
from app.infrastructure.security_headers import SecurityHeadersMiddleware
from app.routers import (
    admin,
    attendance,
    auth,
    corrections,
    cron,
    display,
    kiosks,
    leave,
    punches,
    reports,
    users,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
APP_VERSION = "1.2.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    docs_url = "/docs" if settings.docs_enabled else None
    redoc_url = "/redoc" if settings.docs_enabled else None
    openapi_url = "/openapi.json" if settings.docs_enabled else None

    app = FastAPI(
        title=settings.app_name,
        version=APP_VERSION,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.security_headers:
        app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(kiosks.router)
    app.include_router(punches.router)
    app.include_router(attendance.router)
    app.include_router(leave.router)
    app.include_router(corrections.router)
    app.include_router(display.router)
    app.include_router(reports.router)
    app.include_router(admin.router)
    app.include_router(cron.router)

    @app.on_event("startup")
    def _startup() -> None:
        ApplicationBootstrap(settings).run()

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": APP_VERSION,
            "env": settings.app_env,
        }

    if STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(STATIC_DIR / "index.html")

        @app.get("/display/{token}")
        def display_page(token: str):
            return FileResponse(STATIC_DIR / "display.html")

        @app.get("/login")
        @app.get("/punch")
        @app.get("/kiosk")
        @app.get("/kiosk/pair")
        @app.get("/dashboard")
        @app.get("/admin")
        @app.get("/leave")
        @app.get("/approvals")
        def spa_routes():
            return FileResponse(STATIC_DIR / "index.html")

    return app

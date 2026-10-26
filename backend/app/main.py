"""ASGI entrypoint — thin module that exposes `app` for uvicorn."""

from app.factory import create_app

app = create_app()

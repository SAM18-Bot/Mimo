"""ASGI entry point for deployments configured to start `uvicorn main:app`."""

from server.main import app

__all__ = ["app"]

"""Top-level API router registration."""

from fastapi import APIRouter

from backend.app.api.datasets import router as datasets_router
from backend.app.api.health import router as health_router
from backend.app.api.shelters import router as shelters_router
from backend.app.api.villages import router as villages_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(villages_router)
api_router.include_router(shelters_router)
api_router.include_router(datasets_router)

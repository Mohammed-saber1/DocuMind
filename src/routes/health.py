"""Base API routes."""
from fastapi import APIRouter, Depends
from core.config import get_settings, Settings

base_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1"],
)


@base_router.get("/")
async def welcome(settings: Settings = Depends(get_settings)):
    """
    API welcome endpoint.
    
    Returns application name, version, and status.
    """
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "status": "healthy"
    }


@base_router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns OK if service is running.
    """
    return {"status": "ok"}

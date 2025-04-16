from fastapi import APIRouter

from src.api.main_endpoints import app_router

main_router = APIRouter(prefix="/api")

main_router.include_router(app_router.router)

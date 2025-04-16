from fastapi import FastAPI
from src.api.main_endpoints.router import main_router
from src.api.v1.router import api_router
from src.api.v2.router import api_v2_router


def include_routers(app: FastAPI):
    app.include_router(main_router)
    app.include_router(api_router)
    app.include_router(api_v2_router)

from fastapi import APIRouter

from src.api.v2.endpoints import check

api_v2_router = APIRouter(prefix="/api/v2")

# api_router.include_router(users.router, prefix="/user", tags=["user"])
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(profile.router, prefix="/user", tags=["profile"])
# api_router.include_router(app_router.router)
# api_router.include_router(image.router, prefix="/image", tags=["image"])
api_v2_router.include_router(check.router, prefix="/checks", tags=["checks"])
# api_router.include_router(item.router, prefix="/check", tags=["item"])
# api_router.include_router(token.router, prefix="/token", tags=["token"])

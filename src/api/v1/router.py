from fastapi import APIRouter
from src.api.v1.endpoints import users, websockets, app_router, profile, image, check, test, token, item


api_router = APIRouter()

api_router.include_router(users.router, prefix="/user", tags=["user"])
api_router.include_router(profile.router, prefix="/user", tags=["profile"])
api_router.include_router(app_router.router)
api_router.include_router(image.router, prefix="/image", tags=["image"])
api_router.include_router(check.router, prefix="/check", tags=["check"])
api_router.include_router(item.router, prefix="/check", tags=["item"])
api_router.include_router(token.router, prefix="/token", tags=["token"])

api_router.include_router(websockets.router, tags=["websockets"])

api_router.include_router(test.router, prefix="/test", tags=["test"])

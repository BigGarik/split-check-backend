from fastapi import APIRouter

from src.api.v2.endpoints import check, web_ui, auth_firebase, avatars, item
from src.config import ENVIRONMENT

api_v2_router = APIRouter(prefix="/api/v2")

# api_router.include_router(users.router, prefix="/user", tags=["user"])
api_v2_router.include_router(auth_firebase.router, prefix="/auth_firebase", tags=["auth_firebase"])
api_v2_router.include_router(avatars.router, prefix="/avatars", tags=["avatars"])
# api_router.include_router(profile.router, prefix="/user", tags=["profile"])
# api_router.include_router(app_router.router)
# api_v2_router.include_router(image.router, prefix="/images", tags=["images"])
api_v2_router.include_router(check.router, prefix="/checks", tags=["checks"])
api_v2_router.include_router(item.router, prefix="/checks", tags=["items"])
# api_router.include_router(token.router, prefix="/token", tags=["token"])


if ENVIRONMENT != "prod":
    api_v2_router.include_router(web_ui.router, prefix="/webui", tags=["webui"])
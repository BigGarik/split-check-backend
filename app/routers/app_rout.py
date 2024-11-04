from fastapi import Request, APIRouter
from fastapi.responses import RedirectResponse
from loguru import logger


router = APIRouter(prefix="/app", tags=["app"])


@router.get("")
async def download_app(request: Request):
    user_agent = request.headers.get("user-agent", "").lower()

    # ios_app_url = "https://apps.apple.com/app/your-app-id"
    # android_app_url = "https://play.google.com/store/apps/details?id=your.package.name"

    ios_app_url = "https://apps.apple.com"
    android_app_url = "https://play.google.com"

    if "iphone" in user_agent or "ipad" in user_agent or "ipod" in user_agent:
        return RedirectResponse(ios_app_url)
    elif "android" in user_agent:
        return RedirectResponse(android_app_url)
    else:
        return {"error": "Неподдерживаемое устройство"}
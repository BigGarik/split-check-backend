from fastapi import Request, APIRouter
from fastapi.responses import RedirectResponse

from src.config.settings import settings
from src.config.type_events import EVENT_DESCRIPTIONS

router = APIRouter()


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


@router.get("/events", summary="Получить типы событий", response_description="Список типов событий с описанием")
async def get_events():
    return [
        {"event_type": event, "description": description}
        for event, description in EVENT_DESCRIPTIONS.items()
    ]


@router.get("/share/{uuid}")
async def redirect_to_app(uuid: str):
    # Генерируем deep link, который будет открыт в приложении
    deep_link_url = settings.deep_link_url
    deep_link = f"{deep_link_url}{uuid}"

    # Редиректим пользователя на deep link
    return RedirectResponse(url=deep_link)

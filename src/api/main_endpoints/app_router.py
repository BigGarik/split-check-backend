import logging

from fastapi import Request, APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from starlette.responses import HTMLResponse

from src.api.deps import get_current_user
from src.config import config
from src.config.type_events import EVENT_DESCRIPTIONS
from src.models import User
from src.redis import redis_client
from src.schemas.app import LogLevelUpdateRequest
from src.version import APP_VERSION

router = APIRouter()


@router.post("/log-level")
async def set_log_level(
        req: LogLevelUpdateRequest,
        user: User = Depends(get_current_user),
):
    if user.id not in config.app.admin_ids:
        raise HTTPException(status_code=403, detail="Forbidden")
    level = req.level.upper()
    if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        raise HTTPException(status_code=400, detail=f"Invalid log level: {level}")

    logger = logging.getLogger(config.app.service_name)
    logger.setLevel(level)

    for handler in logger.handlers:
        handler.setLevel(level)

    redis_key = f"{config.app.service_name}:log_level"

    # Кэширование в Redis
    await redis_client.set(
        redis_key,
        level
    )

    return {"message": f"Log level changed to {level}"}


@router.get("/download")
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


@router.get("/share/{uuid}", response_class=HTMLResponse)
async def redirect_to_app(uuid: str):
    html_content = """
    <html>
        <head>
            <title>Check Sharing</title>
        </head>
        <body>
            <h1>Check Shared Successfully!</h1>
        </body>
    </html>
    """
    return html_content


@router.get("/version")
async def read_version():
    return {"version": APP_VERSION}


@router.get("/health")
async def health_check():
    return {"status": "ok"}
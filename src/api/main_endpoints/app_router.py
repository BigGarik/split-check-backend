from fastapi import Request, APIRouter
from fastapi.responses import RedirectResponse
from starlette.responses import HTMLResponse

from src.config.type_events import EVENT_DESCRIPTIONS
from src.version import APP_VERSION

router = APIRouter()


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
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates

router = APIRouter()


templates = Jinja2Templates(directory="templates")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")


@router.get("", response_class=HTMLResponse)
async def get_websocket_page(request: Request):
    return templates.TemplateResponse("upload_image.html", {"request": request})


@router.get("/ws")
async def test_ws_page(request: Request):
    return templates.TemplateResponse("ws.html", {"request": request})


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

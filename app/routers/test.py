import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
import json

from jose import JWTError


router_test = APIRouter()

templates = Jinja2Templates(directory="templates")

load_dotenv()

access_secret_key = os.getenv('ACCESS_SECRET_KEY')
refresh_secret_key = os.getenv('REFRESH_SECRET_KEY')
access_token_expire_minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))
refresh_token_expire_days = int(os.getenv('REFRESH_TOKEN_EXPIRE_MINUTES'))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router_test.get("/", response_class=HTMLResponse)
async def get_websocket_page(request: Request):
    return templates.TemplateResponse("upload_image.html", {"request": request})


@router_test.get("/test_ws")
async def test_ws_page(request: Request):
    return templates.TemplateResponse("ws.html", {"request": request})


# Маршрут для отправки сообщения конкретному пользователю
@router_test.post("/send-message/{user_id}")
async def send_message_to_user(user_id: str, message: str):
    # await ws_manager.send_personal_message(message, user_id)
    return {"message": f"Message sent to {user_id}"}

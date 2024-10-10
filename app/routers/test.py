import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
import json

from jose import JWTError
from sqlalchemy.orm import Session

from ..auth import authenticate_user, create_token, verify_token
from ..database import get_db
from ..redis import redis_queue_publish

router_test = APIRouter()

templates = Jinja2Templates(directory="templates")

load_dotenv()

access_secret_key = os.getenv('ACCESS_SECRET_KEY')
refresh_secret_key = os.getenv('REFRESH_SECRET_KEY')
access_token_expire_minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))
refresh_token_expire_days = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS'))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router_test.get("/", response_class=HTMLResponse)
async def get_websocket_page(request: Request):
    return templates.TemplateResponse("upload_image.html", {"request": request})


@router_test.get("/test/{val}")
async def read_test(val: str):
    msg = {
        "target_user_id": "edemerchan@yandex.ru",
        "payload": {
            "some_key": val
        }
    }

    str_msg = json.dumps(msg)
    # Отправляем сообщение в очередь
    await redis_queue_publish(str_msg)

    return {"message": "Test route working!"}


@router_test.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router_test.post("/refresh/")
async def refresh_access_token(refresh_token: str = Depends(oauth2_scheme)):
    try:
        # 1. Проверка Refresh токена
        email = verify_token(secret_key=refresh_secret_key, token=refresh_token)

        # 2. Создаем новый Access токен
        new_access_token = create_token(data={"sub": email},
                                        token_expire_minutes=access_token_expire_minutes,
                                        secret_key=access_secret_key)

        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router_test.get("/test_ws")
async def test_ws_page(request: Request):
    return templates.TemplateResponse("ws.html", {"request": request})


# Маршрут для отправки сообщения конкретному пользователю
@router_test.post("/send-message/{user_id}")
async def send_message_to_user(user_id: str, message: str):
    #await ws_manager.send_personal_message(message, user_id)
    return {"message": f"Message sent to {user_id}"}

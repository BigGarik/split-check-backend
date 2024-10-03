from celery import chain
from fastapi import APIRouter
from fastapi import Request
from fastapi.templating import Jinja2Templates
import json

from ..redis import redis_queue_publish

router_test = APIRouter()

templates = Jinja2Templates(directory="templates")


@router_test.get("/test/{val}")
async def read_test(val: str):
    msg = {
        "target_user_id": "edemerchan@yandex.ru",
        "payload": {
            "some_key": val
        }
    }

    str_msg = json.dumps(msg)
    #Отправляем сообщение в очередь
    await redis_queue_publish(str_msg)

    return {"message": "Test route working!"}


@router_test.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router_test.get("/test_ws")
async def test_ws_page(request: Request):
    return templates.TemplateResponse("ws.html", {"request": request})


# Маршрут для отправки сообщения конкретному пользователю
@router_test.post("/send-message/{user_id}")
async def send_message_to_user(user_id: str, message: str):
    #await ws_manager.send_personal_message(message, user_id)
    return {"message": f"Message sent to {user_id}"}

import json
import logging
import os
import random

import shutil
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse

from app.database import redis_client, nats_client
from app.routers.ws import ws_manager
from external_services.api_anthropic import recognize_check
from fastapi import APIRouter

router_webapp = APIRouter()

logger = logging.getLogger(__name__)


UPLOAD_DIRECTORY = "images"


@router_webapp.get("/test/")
def test():
    print("Hello World")
    return {"message": "Hello World"}


@router_webapp.post("/upload-image/")
async def upload_image():
    recognized_json = {
        "restaurant": "Веранда",
        "table_number": "110",
        "order_number": "57",
        "date": "17.08.2024",
        "time": "17:28",
        "waiter": "Нурсултан А.",
        "items": [
            {
                "id": 1,
                "name": "Мохито 300 мл б/а",
                "quantity": 1,
                "price": 65000
            },
            {
                "id": 2,
                "name": "Вода Chortog 750мл без газа холодный",
                "quantity": 1,
                "price": 38000
            },
            {
                "id": 3,
                "name": "Paulaner",
                "quantity": 2,
                "price": 330000
            },
            {
                "id": 4,
                "name": "пиво Eggenberg Freibie г 330 мл",
                "quantity": 2,
                "price": 190000
            },
            {
                "id": 5,
                "name": "Ризотто с трюфелем",
                "quantity": 1,
                "price": 186000
            },
            {
                "id": 6,
                "name": "Наггетсы из индейки 5 шт",
                "quantity": 2,
                "price": 144000
            },
            {
                "id": 7,
                "name": "Картофель фри",
                "quantity": 1,
                "price": 45000
            },
            {
                "id": 8,
                "name": "Суши лосось",
                "quantity": 6,
                "price": 270000
            },
            {
                "id": 9,
                "name": "Кейк-попс с декором",
                "quantity": 2,
                "price": 70000
            },
            {
                "id": 10,
                "name": "Пицца с грушей с горго нзолой",
                "quantity": 1,
                "price": 155000
            },
            {
                "id": 11,
                "name": "Чай Ассам",
                "quantity": 1,
                "price": 45000
            },
            {
                "id": 12,
                "name": "Лимон добавка",
                "quantity": 1,
                "price": 12000
            },
            {
                "id": 13,
                "name": "Куриная котлета с гарн иром картофельное пюре",
                "quantity": 1,
                "price": 84000
            },
            {
                "id": 14,
                "name": "Макаронс малина",
                "quantity": 2,
                "price": 50000
            },
            {
                "id": 15,
                "name": "Макаронс шоколад",
                "quantity": 3,
                "price": 75000
            },
            {
                "id": 16,
                "name": "Вода Chortog 750мл без газа холодный",
                "quantity": 1,
                "price": 38000
            },
            {
                "id": 17,
                "name": "кетчуп добавка",
                "quantity": 1,
                "price": 20000
            }
        ],
        "subtotal": 1817000,
        "service_charge": {
            "name": "Сервисный сбор 12%",
            "amount": 218040
        },
        "vat": {
            "rate": 0,
            "amount": 0
        },
        "total": 2035040
    }
    response_data = {
        "message": f"Successfully uploaded image.jpg",
        "uuid": "9d0dd3fc-86e1-401a-bf0e-9f2d511b2442",
        "recognized_json": recognized_json
    }

    number = random.randrange(1, 11)

    if number < 4:
        return JSONResponse(content={"message": f"random {number}. No file response"}, status_code=400)
    else:
        return JSONResponse(content=response_data, status_code=200)


# @router_webapp.post("/upload-image/")
# async def upload_image(file: UploadFile = File(...)):
#     uuid_dir = uuid.uuid4()
#     upload_directory = os.path.join(UPLOAD_DIRECTORY, str(uuid_dir))
#     if not file:
#         return JSONResponse(content={"message": "No file sent"}, status_code=400)
#
#     if not file.content_type.startswith("image/"):
#         return JSONResponse(content={"message": "File is not an image"}, status_code=400)
#
#     if not os.path.exists(upload_directory):
#         os.makedirs(upload_directory)
#
#     file_path = os.path.join(upload_directory, file.filename)
#
#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)
#     response = recognize_check(upload_directory)
#
#     # Данные для сохранения в Redis
#     redis_data = {
#         "message": f"Successfully uploaded {file.filename}",
#         "response": response
#     }
#
#     # Сериализуем данные в JSON
#     json_data = json.dumps(redis_data)
#
#     # Сохраняем данные в Redis
#     uuid_str = str(uuid_dir)
#     await redis_client.set(uuid_str, json_data)
#
#     # Устанавливаем время жизни ключа (например, 1 час = 3600 секунд)
#     await redis_client.expire(uuid_str, 3600 * 24)
#
#     response_data = {
#         "message": f"Successfully uploaded {file.filename}",
#         "uuid": uuid_str,
#         "response": response
#     }
#
#     final_json_string = json.dumps(response_data, ensure_ascii=False, indent=2)
#     logger.info(final_json_string)
#     return JSONResponse(content=final_json_string, status_code=200)


@router_webapp.get("/get_check")
@router_webapp.post("/get_check")
async def get_value(key: str = Query(None), request: dict = None):
    if request and "key" in request:
        key = request["key"]

    if not key:
        raise HTTPException(status_code=400, detail="Key is required")

    value = await redis_client.get(key)
    logger.info(f"Retrieved value for key '{key}': {value}")

    if value is None:
        return JSONResponse(content={"message": "Key not found"}, status_code=404)

    response = json.loads(value)
    return response


# Маршрут для отправки сообщения конкретному пользователю
@router_webapp.post("/send-message/{user_id}")
async def send_message_to_user(user_id: str, message: str):
    await ws_manager.send_personal_message(message, user_id)
    return {"message": f"Message sent to {user_id}"}


# Маршрут для отправки сообщения всем подключенным пользователям
@router_webapp.post("/broadcast")
async def broadcast_message(message: str):
    await ws_manager.broadcast(message)
    return {"message": "Message broadcasted to all users"}


@router_webapp.post("/update")
async def broadcast_message_to_all(message: str):
    """
    Отправляет сообщение в топик 'broadcast' в NATS. Все WebSocket-подключения его получат.
    """
    # Отправляем сообщение в NATS в топик 'broadcast'
    await nats_client.publish("broadcast", message.encode())
    return {"status": "Message sent to all users"}



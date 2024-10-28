import json
import os
import random

from dotenv import load_dotenv
from loguru import logger

from app.crud import add_check_to_database
from app.routers.ws import ws_manager
from services.classifier_image import classifier_image

load_dotenv()

redis_expiration = os.getenv("REDIS_EXPIRATION")


async def recognize_image(check_uuid: str, user_id: int, file_location_directory: str, file_name: str, redis_client):
    # 1. сначала классифицируем изображение и если все ок, то отправляем на распознавание
    # Классифицируем изображение
    image = os.path.join(file_location_directory, file_name)
    logger.info(f"Image location: {image}")
    try:
        result = await classifier_image(image)
        if result == "Allowed Content":
            logger.info(f"Image classification result: {result}")
            # 2. Распознаем чек через нейронку и получаем в ответ JSON
            # recognized_json = recognize_check(file_location_directory)
        else:
            logger.info(f"Image classification result: {result}")
    except Exception as e:
        logger.error(e)

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

    # response_data = {
    #     "message": f"Successfully uploaded image",
    #     "check_uuid": check_uuid,
    #     "recognized_json": recognized_json
    # }

    # Сохранить распознанные данные в Redis и базу данных
    await add_check_to_database(check_uuid, user_id, recognized_json)

    # Сериализация и сохранение в Redis f"check_uuid_{check_uuid}"
    redis_key = f"check_uuid:{check_uuid}"
    task_data = json.dumps(recognized_json)
    await redis_client.set(redis_key, task_data, expire=redis_expiration)

##################### На время тестов ############################
    # number = random.randrange(1, 11)
    #
    # import time
    # time.sleep(2)  # Симуляция длительной обработки
    #
    # if number < 4:
    #     response_message = {"message": f"random {number}. No file response"}
    #     status_code = 400
    # else:
    #     response_message = response_data
    #     status_code = 200
##################################################################
    msg = {
        "type": "imageRecognitionEvent",
        "payload": {
            "uuid": check_uuid,
        },
    }
    msg_to_ws = json.dumps(msg)
    await ws_manager.send_personal_message(msg_to_ws, user_id)

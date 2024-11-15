import json
import os

from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.websockets import ws_manager
from src.config.settings import settings
from src.managers.check_manager import CheckManager, get_check_manager
from src.redis import redis_client
from src.repositories.check import add_check_to_database
from src.services.classifier.classifier_image import classifier_image


async def recognize_image_task(
        check_uuid: str,
        user_id: int,
        file_location_directory: str,
        file_name: str,
        check_manager: CheckManager = Depends(get_check_manager)
):
    """ Обработка изображения: классификация и распознавание. """

    image_path = os.path.join(file_location_directory, file_name)
    logger.info(f"Processing image at {image_path} for user_id {user_id}")

    try:
        # Классификация изображения
        classification_result = await classifier_image(image_path)
        if classification_result == "Allowed Content":
            # Распознавание чека
            # recognized_json = await recognize_check_by_anthropic(file_location_directory)

            # постоянный ответ для отладки
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

            logger.debug(f"Recognition completed for check_uuid {check_uuid}")

            await check_manager.add_check(user_id, check_uuid, recognized_json)

        else:
            error_msg = {
                    "type": settings.Events.IMAGE_RECOGNITION_EVENT_STATUS,
                    "status": "error",
                    "message": f"Image classification failed with result: {classification_result}"
                }
            msg_to_ws = json.dumps(error_msg)
            await ws_manager.send_personal_message(msg_to_ws, user_id)

            logger.warning(f"Image classification for check_uuid {check_uuid} failed with result: {classification_result}")
    except Exception as e:

        error_msg = {
            "type": settings.Events.IMAGE_RECOGNITION_EVENT_STATUS,
            "status": "error",
            "message": f"Error processing image {check_uuid}: {e}"
        }
        msg_to_ws = json.dumps(error_msg)
        await ws_manager.send_personal_message(msg_to_ws, user_id)

        logger.error(f"Error processing image {check_uuid}: {e}")

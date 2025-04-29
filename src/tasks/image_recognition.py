import json
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import ENVIRONMENT, REDIS_EXPIRATION
from src.config.type_events import Events
from src.redis import redis_client
from src.repositories.check import add_check_to_database
from src.services.ai.api_anthropic import recognize_check_by_anthropic
from src.services.classifier.classifier_image import classifier_image
from src.utils.notifications import create_event_message
from src.utils.system import get_memory_usage
from src.websockets.manager import ws_manager

logger = logging.getLogger(__name__)


def calculate_price(json_data):
    """
    Вычисляет и записывает цену для каждого элемента в JSON.
    Перезаписывает price, если он уже есть.
    Считает quantity равным 1, если оно меньше 1.

    Args:
        json_data (dict): JSON данные.

    Returns:
        dict: JSON данные с добавленными ценами.
    """

    for item in json_data['items']:
        # Проверяем quantity и устанавливаем значение 1, если оно меньше 1
        quantity = item['quantity']
        if quantity < 1:
            quantity = 1

        # Вычисляем и записываем цену
        item['price'] = item['sum'] / quantity

    return json_data


async def recognize_image_task(
        check_uuid: str,
        user_id: int,
        file_location_directory: str,
        file_name: str,
        session: AsyncSession
):
    """ Обработка изображения: классификация и распознавание. """

    image_path = os.path.join(file_location_directory, file_name)
    logger.info(f"Начало обработки изображения {image_path} для пользователя  {user_id}, память: {get_memory_usage():.2f} MB")

    try:
        # Классификация изображения
        classification_result = await classifier_image(image_path)
        if classification_result == "Allowed Content":
            # Распознавание чека
            if ENVIRONMENT == "prod":
                recognized_json = await recognize_check_by_anthropic(file_location_directory)
            else:
                recognized_json = {
                    "restaurant": "Bistro",
                    "table_number": "1",
                    "order_number": "998",
                    "date": "19.11.2024",
                    "time": "13:26",
                    "waiter": "Kacca 2",
                    "items": [
                        {
                            "id": 1,
                            "name": "Бабушкин хлеб",
                            "quantity": 2,
                            "sum": 4000
                        },
                        {
                            "id": 2,
                            "name": "Солянка",
                            "quantity": 1,
                            "sum": 16000
                        },
                        {
                            "id": 3,
                            "name": "Куриный суп с лапшой",
                            "quantity": 1,
                            "sum": 16000
                        },
                        {
                            "id": 4,
                            "name": "Говядина с грибами",
                            "quantity": 1,
                            "sum": 21000
                        },
                        {
                            "id": 5,
                            "name": "Рис отварной",
                            "quantity": 0.5,
                            "sum": 3500
                        },
                        {
                            "id": 6,
                            "name": "Гречка",
                            "quantity": 0.5,
                            "sum": 3000
                        },
                        {
                            "id": 7,
                            "name": "Ёжик из курицы",
                            "quantity": 1,
                            "sum": 12000
                        },
                        {
                            "id": 8,
                            "name": "Сендвич с курицей",
                            "quantity": 1,
                            "sum": 13000
                        }
                    ],
                    "subtotal": 88500,
                    "service_charge": {
                        "name": "",
                        "amount": 0
                    },
                    "vat": {
                        "rate": 0,
                        "amount": 0
                    },
                    "total": 88500
                }
            # recognized_json = calculate_price(recognized_json)
            #
            # logger.debug(f"Recognition completed for check_uuid {check_uuid}")
            #
            # await check_manager.add_check(user_id, check_uuid, recognized_json)

            check_data = await add_check_to_database(session, check_uuid, user_id, recognized_json)

            redis_key = f"check_uuid:{check_uuid}"

            await redis_client.set(redis_key, json.dumps(check_data), expire=REDIS_EXPIRATION)

            msg = create_event_message(
                message_type=Events.IMAGE_RECOGNITION_EVENT,
                payload={"uuid": check_uuid}
            )

            await ws_manager.send_personal_message(
                message=json.dumps(msg),
                user_id=user_id
            )

        else:
            error_msg = {
                "type": Events.IMAGE_RECOGNITION_EVENT_STATUS,
                "status": "error",
                "message": f"Image classification failed with result: {classification_result}"
            }
            msg_to_ws = json.dumps(error_msg)
            await ws_manager.send_personal_message(msg_to_ws, user_id)

            logger.warning(
                f"Image classification for check_uuid {check_uuid} failed with result: {classification_result}")
    except Exception as e:

        error_msg = {
            "type": Events.IMAGE_RECOGNITION_EVENT_STATUS,
            "status": "error",
            "message": f"Error processing image {check_uuid}: {e}"
        }
        msg_to_ws = json.dumps(error_msg)
        await ws_manager.send_personal_message(msg_to_ws, user_id)

        logger.error(f"Error processing image {check_uuid}: {e}")
    logger.info(f"Конец обработки изображения {image_path} для пользователя  {user_id}, память: {get_memory_usage():.2f} MB")
